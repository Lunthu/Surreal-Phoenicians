# 🌊 Surreal Phoenicians

**Surreal Phoenicians** is a text‑based economic strategy and management game set during the era of Phoenician maritime trade.  
You play as a trader sailing between ancient ports, buying and selling goods, upgrading your ship, negotiating prices, and dealing with random events — all powered by a unique **surreal number**–based economy.

---

## 🎮 Features

- **Playable trading simulation** between Carthage, Tyre, and Gadir (easily extensible to more cities).
- **Surreal number pricing**:  
  Prices are represented as _a + bε + cω_, giving you finite values (`a`), infinitesimal negotiation edges (`ε`), and infinite constraints (`ω` for monopolies/embargoes).
- **Negotiation mechanic** using Dedekind cuts to resolve fair prices in trading.
- **Dynamic supply & demand** with 14‑day market refreshes and specialty goods per city.
- **Random events** at sea: pirates, storms, traders, favorable winds.
- **Victory condition**: earn enough to buy a grand house in Carthage.
- **Statistics tracking** for your trades, routes, cargo, and events.

---

## 🗂 Project Structure

- `SurrealNumber` — core class for surreal‑algebra economy.
- `Good`, `City`, `Route` — data models for game world entities.
- `NegotiationCut` — implements simple midpoint settlement between buyer/seller sets.
- `GameState` — holds all persistent game data, pricing logic, and simulation rules.
- `GameEngine` — runs the text UI game loop, handles actions, and displays screens.

---

## 📦 Requirements

- Python **3.8+**
- No external libraries required — uses only the standard library.

---

## ▶️ How to Run

1. **Clone or download** this repository.
2. Place `surreal_phoenicians.py` (or the provided script file) in your working directory.
3. Run the game:

   ```bash
   python surreal_phoenicians.py
