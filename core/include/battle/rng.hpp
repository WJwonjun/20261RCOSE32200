#pragma once
#include <cstdint>

namespace battle {

// PCG64 — Permuted Congruential Generator (64-bit output, 128-bit state).
// Reference: O'Neill, "PCG: A Family of Better Random Number Generators", 2014.
class PCG64 {
public:
    explicit PCG64(uint64_t seed = 0x853c49e6748fea9bULL) noexcept {
        state_ = 0u;
        inc_   = (seed << 1u) | 1u; // inc must be odd
        next_uint64();               // warm up
        state_ += seed;
        next_uint64();               // warm up
    }

    // Returns a uniformly distributed 64-bit integer.
    uint64_t next_uint64() noexcept {
        uint64_t old = state_;
        state_ = old * 6364136223846793005ULL + inc_;
        uint64_t xorshifted = ((old >> 18u) ^ old) >> 27u;
        uint64_t rot = old >> 59u;
        uint32_t out32 = (uint32_t)((xorshifted >> rot) | (xorshifted << ((-rot) & 31)));
        // Extend to 64-bit by generating a second word
        old = state_;
        state_ = old * 6364136223846793005ULL + inc_;
        xorshifted = ((old >> 18u) ^ old) >> 27u;
        rot = old >> 59u;
        uint32_t out32b = (uint32_t)((xorshifted >> rot) | (xorshifted << ((-rot) & 31)));
        return ((uint64_t)out32 << 32u) | out32b;
    }

    // Returns a double in [0.0, 1.0).
    double next_double() noexcept {
        return (double)(next_uint64() >> 11u) * (1.0 / (double)(1ULL << 53));
    }

    // Returns an integer in [lo, hi] inclusive.
    int range(int lo, int hi) noexcept {
        uint64_t span = (uint64_t)(hi - lo + 1);
        return lo + (int)(next_uint64() % span);
    }

    uint64_t state() const noexcept { return state_; }
    uint64_t inc()   const noexcept { return inc_;   }

private:
    uint64_t state_;
    uint64_t inc_;
};

} // namespace battle
