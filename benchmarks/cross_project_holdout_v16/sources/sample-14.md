# Blending Modes: Accuracy vs Performance

## Basic / Minimum
- Minimal blending operations

**Pros**
- Lowest GPU cost
- Best for very low-end devices

**Cons**
- Visual artifacts in many PS2 titles
- Reduced accuracy

## Medium
- Partial blending accuracy

**Pros**
- Balanced performance and visuals
- Good default for mid-range devices

**Cons**
- Some effects may still be incorrect

## Full
- High blending accuracy

**Pros**
- Corrects most visual effects
- Good behavioral accuracy

**Cons**
- Moderate GPU cost

## Ultra
- Full PS2 blending emulation

**Pros**
- Highest visual and behavioral accuracy
- Fixes post-processing and transparency effects

**Cons**
- Highest GPU load
- Can reduce performance on weak hardware

## Practical Guidance
- Accuracy testing → Full or Ultra
- Playability on low-end devices → Medium or lower