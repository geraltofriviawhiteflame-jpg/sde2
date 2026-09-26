# LLD / OOD Practice

Amazon-style LLD round: clarify requirements → identify entities → define interfaces → code the core in ~35–40 min → discuss concurrency, extension, and testing.

**Format per problem folder** (`prep/lld/<problem>/`):
- `requirements.md` — functional + non-functional, clarified constraints
- solution code (Java preferred for Amazon loops; Python fine elsewhere)
- `tradeoffs.md` — what you'd change at scale, where you'd add a DB/persistence

## Problem queue (in order)

- [ ] **Parking Lot** (W1) — spots, vehicles, ticketing, fee strategies
- [ ] **ATM** (W2) — states, card/session, dispenser denominations, transaction safety
- [ ] **BookMyShow** (W3) — seat-lock race condition, shows, pricing — *the concurrency classic*
- [ ] **Elevator System** (W4) — scheduling algorithm, multiple cars
- [ ] Splitwise / expense sharing
- [ ] LRU Cache (design + OOD wrapper)
- [ ] Coffee Vending Machine (state machine)
- [ ] Tic-tac-toe / Snake & Ladder (game loop, winner detection)
- [ ] Logger + Rate Limiter (token bucket OOD)
- [ ] Order/Inventory (intro to outbox + saga — bridges into HLD)

## Must-hit talking points every time

1. Interfaces over concretes; Strategy pattern for fees/pricing/scheduling
2. Concurrency: which shared state? which lock? optimistic vs pessimistic? (BookMyShow seat lock!)
3. Idempotency of operations (ATM dispense retry!)
4. Persistence boundary: what would you store, what's derived?
5. Tests for the 2–3 critical paths
