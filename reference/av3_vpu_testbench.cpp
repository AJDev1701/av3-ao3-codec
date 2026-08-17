/**
 * AV3 VPU Reference Testbench — C++17
 * Spec: SPEC_AV3_ALPHA_OMEGA_03 | Phase 1 Foundation
 * Build: g++ -std=c++17 -Wall -Wextra -Werror -pedantic -O2 -o av3_testbench av3_vpu_testbench.cpp
 */
#include <cstdint>
#include <cmath>
#include <cstdio>
#include <cassert>
#include <array>
#include <algorithm>
#include <string_view>

// ── VPU Header (64-bit) ───────────────────────────────────────
enum class VPU_Mode : uint8_t { PASSTHROUGH_2D=0b000, VOLUMETRIC_PHASE=0b001 };

#pragma pack(push,1)
struct VPU_Header {
    uint32_t ver:3, mode:3, fb:1, phase_clk:8, depth_res:8, eps_pow:8, reserved0:1;
    uint16_t s_squish;
    uint16_t reserved1;
    [[nodiscard]] bool is_av3()        const noexcept { return ver==0b011; }
    [[nodiscard]] bool is_volumetric() const noexcept { return mode==static_cast<uint8_t>(VPU_Mode::VOLUMETRIC_PHASE); }
    [[nodiscard]] bool fallback_active() const noexcept { return fb==1; }
};
#pragma pack(pop)
static_assert(sizeof(VPU_Header)==8,"VPU_Header must be 8 bytes");

// ── Gate FSM ─────────────────────────────────────────────────
enum class NPU_Gate:uint8_t { STATIC_ANCHOR=0b00,QUADRATURE_0DEG=0b01,QUADRATURE_90DEG=0b10,SQUISH_RESET=0b11 };
constexpr std::string_view gate_name(NPU_Gate g) noexcept {
    switch(g){
        case NPU_Gate::STATIC_ANCHOR:    return "STATIC_ANCHOR   [00]";
        case NPU_Gate::QUADRATURE_0DEG:  return "QUADRATURE_0DEG [01]";
        case NPU_Gate::QUADRATURE_90DEG: return "QUADRATURE_90DEG[10]";
        case NPU_Gate::SQUISH_RESET:     return "SQUISH_RESET    [11]";
    } return "UNKNOWN";
}
struct NPU_GateController {
    NPU_Gate current_gate=NPU_Gate::STATIC_ANCHOR;
    uint32_t cycle_count=0;
    bool phase_synced=false;
    uint8_t observer_count=0;
    static constexpr uint8_t MIN_OBSERVERS=2;
    bool tick(VPU_Header& hdr) noexcept {
        ++cycle_count;
        if(!phase_synced && hdr.is_volumetric()){ hdr.fb=1; current_gate=NPU_Gate::STATIC_ANCHOR; return false; }
        switch(current_gate){
            case NPU_Gate::STATIC_ANCHOR:    current_gate=NPU_Gate::QUADRATURE_0DEG; break;
            case NPU_Gate::QUADRATURE_0DEG:  current_gate=hdr.is_volumetric()?NPU_Gate::QUADRATURE_90DEG:NPU_Gate::STATIC_ANCHOR; break;
            case NPU_Gate::QUADRATURE_90DEG: current_gate=NPU_Gate::SQUISH_RESET; break;
            case NPU_Gate::SQUISH_RESET:     current_gate=NPU_Gate::STATIC_ANCHOR; break;
        } return true;
    }
    [[nodiscard]] bool can_commit() const noexcept { return observer_count>=MIN_OBSERVERS; }
};

// ── Squish Engine ─────────────────────────────────────────────
struct SquishEngine {
    static constexpr float W_N=0.4f,W_U=0.3f,W_R=0.3f;
    static constexpr float EPS_GUARD=1e-9f,EPS_CAP=0.9997f;
    uint8_t eps_power=1;
    struct RegResult { float s_squish,d_ratio,d_asymptotic,eps_eff; bool safe; };
    [[nodiscard]] RegResult compute(float n,float u,float r,float err,float fric,float eps) const noexcept {
        eps=std::min(eps,EPS_CAP);
        float ep=std::pow(eps,static_cast<float>(eps_power));
        float s=W_N*n+W_U*u+W_R*r;
        float dr=(err/(s+EPS_GUARD))+fric;
        float da=dr/(dr+ep);
        return {s,dr,da,ep,ep<1.0f};
    }
};

// ── SPF Guards ────────────────────────────────────────────────
namespace SPF_Guard {
    [[nodiscard]] inline bool partition(uint32_t sz) noexcept { return sz>=4; }
    [[nodiscard]] inline bool observers(uint8_t n)   noexcept { return n>=NPU_GateController::MIN_OBSERVERS; }
}

// ── Main ─────────────────────────────────────────────────────
int main(){
    std::puts("============================================================");
    std::puts("  AV3 VPU Testbench | SPEC_AV3_ALPHA_OMEGA_03 | C++17      ");
    std::puts("============================================================\n");

    VPU_Header hdr{}; hdr.ver=0b011; hdr.mode=static_cast<uint8_t>(VPU_Mode::VOLUMETRIC_PHASE);
    hdr.fb=0; hdr.phase_clk=90; hdr.depth_res=128; hdr.eps_pow=1;
    std::printf("[HEADER] is_av3=%s  volumetric=%s  fb=%s\n",
        hdr.is_av3()?"YES":"NO", hdr.is_volumetric()?"YES":"NO", hdr.fallback_active()?"ACTIVE":"CLEAR");

    NPU_GateController gate; gate.phase_synced=true; gate.observer_count=2;
    std::puts("\n[GATE] Nominal 4-cycle run:");
    for(int i=0;i<4;++i){ gate.tick(hdr); std::printf("  Cycle %d  %-28s  commit=%s\n",i+1,gate_name(gate.current_gate).data(),gate.can_commit()?"ALLOW":"BLOCK"); }

    std::puts("\n[GATE] SPF-1 path (phase_synced=false):");
    NPU_GateController gf; gf.phase_synced=false; gf.observer_count=2;
    bool ok=gf.tick(hdr);
    std::printf("  SPF-1 triggered: %s | FB=%u\n",ok?"NO":"YES",hdr.fb); hdr.fb=0;

    std::puts("\n[SQUISH] eps_pow=1 epsilon=0.85:");
    SquishEngine sq; sq.eps_power=1;
    auto r1=sq.compute(0.5f,0.3f,0.2f,1.0f,0.05f,0.85f);
    std::printf("  S=%.4f D_ratio=%.4f D_asym=%.4f eps^p=%.4f safe=%s\n",r1.s_squish,r1.d_ratio,r1.d_asymptotic,r1.eps_eff,r1.safe?"YES":"NO");

    std::puts("[SQUISH] Singularity cap stress (epsilon=1.0):");
    auto r2=sq.compute(0.1f,0.1f,0.1f,0.5f,0.0f,1.0f);
    std::printf("  eps^p=%.6f safe=%s\n",r2.eps_eff,r2.safe?"YES (LOCK HELD)":"NO (BUG)");
    assert(r2.safe && "Singularity lock invariant violated");

    std::puts("\n[SPF GUARDS]");
    for(uint32_t sz:{256,64,4,2}) std::printf("  SPF-2 block_size=%-4u -> %s\n",sz,SPF_Guard::partition(sz)?"PASS":"BLOCKED");
    for(uint8_t  n:{3,2,1})      std::printf("  SPF-3 N=%-2u        -> %s\n",n,SPF_Guard::observers(n)?"PASS":"BLOCKED");

    assert(hdr.is_av3() && hdr.is_volumetric() && r1.safe && r2.safe);
    std::puts("\n============================================================");
    std::puts("  Testbench COMPLETE — All invariants PASS                  ");
    std::puts("============================================================");
    return 0;
}
