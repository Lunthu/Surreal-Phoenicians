import random
import json
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import math

class SurrealNumber:
    """
    Represents a surreal number in the form: a + b*ε + c*ω
    where a is real (finite), ε is infinitesimal, ω is infinite
    """
    
    def __init__(self, a: float = 0.0, b: float = 0.0, c: float = 0.0):
        self.a = float(a)  # Real component
        self.b = float(b)  # Infinitesimal coefficient  
        self.c = float(c)  # Infinite coefficient
    
    def __str__(self):
        parts = []
        if self.c != 0:
            parts.append(f"{self.c}ω")
        if self.a != 0 or not parts:
            parts.append(f"{self.a}")
        if self.b != 0:
            parts.append(f"{self.b:+}ε")
        return " + ".join(parts).replace("+ -", "- ")
    
    def __repr__(self):
        return f"SurrealNumber({self.a}, {self.b}, {self.c})"
    
    def __add__(self, other):
        if isinstance(other, (int, float)):
            return SurrealNumber(self.a + other, self.b, self.c)
        return SurrealNumber(self.a + other.a, self.b + other.b, self.c + other.c)
    
    def __radd__(self, other):
        return self.__add__(other)
    
    def __sub__(self, other):
        if isinstance(other, (int, float)):
            return SurrealNumber(self.a - other, self.b, self.c)
        return SurrealNumber(self.a - other.a, self.b - other.b, self.c - other.c)
    
    def __mul__(self, scalar):
        if isinstance(scalar, (int, float)):
            return SurrealNumber(self.a * scalar, self.b * scalar, self.c * scalar)
        raise NotImplementedError("Only scalar multiplication supported")
    
    def __rmul__(self, scalar):
        return self.__mul__(scalar)
    
    def __lt__(self, other):
        """Lexicographic comparison: ω then a then ε"""
        if isinstance(other, (int, float)):
            other = SurrealNumber(other)
        
        if self.c != other.c:
            return self.c < other.c
        if self.a != other.a:
            return self.a < other.a
        return self.b < other.b
    
    def __le__(self, other):
        return self < other or self == other
    
    def __gt__(self, other):
        return not self <= other
    
    def __ge__(self, other):
        return not self < other
    
    def __eq__(self, other):
        if isinstance(other, (int, float)):
            other = SurrealNumber(other)
        return abs(self.a - other.a) < 1e-10 and abs(self.b - other.b) < 1e-10 and abs(self.c - other.c) < 1e-10
    
    def __hash__(self):
        """Make SurrealNumber hashable so it can be used in sets"""
        return hash((round(self.a, 10), round(self.b, 10), round(self.c, 10)))
    
    def is_legal(self):
        """Check if this price is legal (no positive infinite component without permits)"""
        return self.c <= 0
    
    def clear_omega(self):
        """Return a copy with omega component set to 0 (permit applied)"""
        return SurrealNumber(self.a, self.b, 0)

@dataclass
class Good:
    id: str
    name: str
    base_a: float
    base_b: float = 0.0
    monopoly: bool = False
    fragile: bool = False
    perishable: bool = False

@dataclass
class CityModifier:
    a_mod: float = 0.0
    b_mod: float = 0.0
    c_mod: float = 0.0  # 0 = no monopoly, 1+ = monopoly/embargo

@dataclass 
class City:
    id: str
    name: str
    region: str
    modifiers: Dict[str, CityModifier] = field(default_factory=dict)
    stock: Dict[str, int] = field(default_factory=dict)
    demand_factors: Dict[str, float] = field(default_factory=dict)

@dataclass
class Route:
    from_city: str
    to_city: str
    min_days: int
    max_days: int
    base_risk: float
    
    def travel_time(self) -> int:
        return random.randint(self.min_days, self.max_days)

@dataclass
class Ship:
    hull_level: int = 1
    rigging_level: int = 1
    cargo_capacity: int = 50
    crew_size: int = 8
    crew_morale: float = 1.0
    special_equipment: List[str] = field(default_factory=list)
    
    def has_hidden_hold(self) -> bool:
        return "hidden_hold" in self.special_equipment

@dataclass
class Charter:
    cities: List[str]
    goods: List[str]
    
    def applies_to(self, city: str, good: str) -> bool:
        return city in self.cities and good in self.goods

class NegotiationCut:
    """Represents a Dedekind cut for negotiation"""
    def __init__(self):
        self.L: List[SurrealNumber] = []  # Left set (seller-leaning) - using list instead of set
        self.R: List[SurrealNumber] = []  # Right set (buyer-leaning)
    
    def add_offer(self, price: SurrealNumber, is_seller: bool):
        if is_seller:
            self.L.append(price)
        else:
            self.R.append(price)
    
    def find_simplest_in_gap(self) -> Optional[SurrealNumber]:
        """Find the simplest surreal number in the gap between L and R"""
        if not self.L or not self.R:
            return None
        
        max_L = max(self.L)
        min_R = min(self.R)
        
        if max_L >= min_R:
            return None  # No gap
        
        # Simple midpoint strategy for the real component
        mid_a = (max_L.a + min_R.a) / 2
        mid_b = 0.0  # Neutral infinitesimal
        mid_c = max(max_L.c, min_R.c)  # Take the constraint level
        
        return SurrealNumber(mid_a, mid_b, mid_c)

class GameState:
    def __init__(self):
        self.current_city = "carthage"
        self.day = 1
        self.money = SurrealNumber(1240, -1, 0)  # Start with reputation edge
        self.ship = Ship()
        self.cargo: Dict[str, int] = {}
        self.charters: List[Charter] = []
        self.reputation = {"merchant_guild": 5}
        
        # Game progression tracking
        self.game_completed = False
        self.owns_house = False
        self.start_money = SurrealNumber(1240, -1, 0)
        self.last_supply_refresh_day = 1  # Track when supplies were last refreshed
        
        # Statistics tracking
        self.stats = {
            "total_trades": 0,
            "goods_bought": {},  # good_id -> total quantity
            "goods_sold": {},   # good_id -> total quantity
            "total_spent": SurrealNumber(),
            "total_earned": SurrealNumber(),
            "cities_visited": set(["carthage"]),
            "routes_traveled": 0,
            "events_encountered": 0,
            "supply_refreshes": 0,  # Track supply refresh events
        }
        
        # Initialize world
        self.goods = self._create_goods()
        self.cities = self._create_cities()
        self.routes = self._create_routes()
        
    def _create_goods(self) -> Dict[str, Good]:
        return {
            "purple_dye": Good("purple_dye", "Purple Dye", 220, -3, True),
            "glass": Good("glass", "Glass", 120, 0, False),
            "olive_oil": Good("olive_oil", "Olive Oil", 40, -1, False, perishable=True),
            "cedar": Good("cedar", "Cedar Timber", 90, -1, False),
            "wine": Good("wine", "Wine", 36, 0, False, fragile=True, perishable=True),
            "salt": Good("salt", "Salt", 18, 1, False),
            "tin": Good("tin", "Tin", 130, 1, False),
            "silver": Good("silver", "Silver", 240, 2, False),
        }
    
    def _create_cities(self) -> Dict[str, City]:
        cities = {
            "carthage": City("carthage", "Carthage", "N. Africa", stock={
                "glass": 18, "olive_oil": 25, "wine": 12, "salt": 30
            }),
            "tyre": City("tyre", "Tyre", "Levant", stock={
                "purple_dye": 5, "glass": 15, "cedar": 8
            }),
            "gadir": City("gadir", "Gadir", "Iberia", stock={
                "silver": 6, "tin": 12, "salt": 20
            })
        }
        
        # Store base stock levels for supply refresh
        self.base_stock_levels = {
            "carthage": {"glass": 18, "olive_oil": 25, "wine": 12, "salt": 30},
            "tyre": {"purple_dye": 5, "glass": 15, "cedar": 8},
            "gadir": {"silver": 6, "tin": 12, "salt": 20}
        }
        
        # Set up city modifiers and stock levels
        cities["carthage"].modifiers = {
            "glass": CityModifier(-8, -1, 0),  # Glass production hub
            "olive_oil": CityModifier(4, 0, 0),  # Festival bonus - high demand
            "wine": CityModifier(2, 0, 0),  # Moderate demand
        }
        
        cities["tyre"].modifiers = {
            "purple_dye": CityModifier(-40, -2, 0),  # Major production center
            "glass": CityModifier(-20, -1, 0),  # Secondary production
            "cedar": CityModifier(-30, -1, 0),  # Local resource
        }
        
        cities["gadir"].modifiers = {
            "purple_dye": CityModifier(0, 0, 1),  # Embargo - can't trade
            "silver": CityModifier(-30, 1, 0),  # Mining region
            "tin": CityModifier(-20, 0, 0),  # Local metal trade
        }
        
        return cities
    
    def _create_routes(self) -> List[Route]:
        return [
            Route("carthage", "gadir", 7, 10, 0.18),
            Route("carthage", "tyre", 12, 16, 0.15),
            Route("tyre", "gadir", 18, 28, 0.22),
            Route("gadir", "carthage", 8, 11, 0.16),
            Route("tyre", "carthage", 11, 15, 0.12),
            Route("gadir", "tyre", 20, 30, 0.25),
        ]
    
    def get_net_worth(self) -> SurrealNumber:
        """Calculate total net worth including cargo value"""
        total_worth = SurrealNumber(self.money.a, self.money.b, self.money.c)
        
        # Add estimated cargo value
        for good_id, quantity in self.cargo.items():
            # Use average of buy/sell prices for estimation
            cities = list(self.cities.keys())
            avg_price = SurrealNumber()
            price_count = 0
            
            for city_id in cities:
                try:
                    sell_price = self.get_price(good_id, city_id, False)
                    if sell_price.is_legal():
                        avg_price = avg_price + sell_price
                        price_count += 1
                except:
                    continue
            
            if price_count > 0:
                avg_price.a /= price_count
                avg_price.b /= price_count
                total_worth = total_worth + (avg_price * quantity)
        
        return total_worth
    
    def check_supply_refresh(self):
        """Check if it's time to refresh city supplies (every 14 days)"""
        days_since_refresh = self.day - self.last_supply_refresh_day
        
        if days_since_refresh >= 14:
            self.refresh_city_supplies()
            self.last_supply_refresh_day = self.day
            return True
        return False
    
    def refresh_city_supplies(self):
        """Refresh supplies in all cities based on their specialties"""
        refresh_messages = []
        
        for city_id, city in self.cities.items():
            base_stocks = self.base_stock_levels[city_id]
            
            for good_id, base_amount in base_stocks.items():
                current_stock = city.stock.get(good_id, 0)
                
                # Production cities get more of their specialty goods
                is_specialty = good_id in city.modifiers and city.modifiers[good_id].a_mod < 0
                
                if is_specialty:
                    # Specialty goods: restore to base + extra production
                    extra_production = random.randint(2, 8)
                    new_stock = base_amount + extra_production
                    refresh_messages.append(f"   📈 {city.name}: {self.goods[good_id].name} +{new_stock - current_stock}")
                else:
                    # Regular goods: restore to base amount with some variance
                    variance = random.randint(-2, 4)
                    new_stock = max(1, base_amount + variance)
                    
                    if new_stock > current_stock:
                        refresh_messages.append(f"   📦 {city.name}: {self.goods[good_id].name} +{new_stock - current_stock}")
                
                city.stock[good_id] = max(current_stock, new_stock)  # Never reduce existing stock
        
        # Update statistics
        self.stats["supply_refreshes"] += 1
        
        return refresh_messages
    
    def get_price(self, good_id: str, city_id: str, is_buying: bool) -> SurrealNumber:
        """Calculate the current price for a good in a city"""
        good = self.goods[good_id]
        city = self.cities[city_id]
        
        # Start with base price
        price = SurrealNumber(good.base_a, good.base_b, 1 if good.monopoly else 0)
        
        # Apply city modifiers
        if good_id in city.modifiers:
            mod = city.modifiers[good_id]
            price.a += mod.a_mod
            price.b += mod.b_mod
            price.c = mod.c_mod if good.monopoly else 0
        
        # Apply charter if available
        for charter in self.charters:
            if charter.applies_to(city_id, good_id):
                price.c = 0  # Charter clears restrictions
        
        # Calculate market spread based on supply/demand dynamics
        stock = city.stock.get(good_id, 0)
        player_cargo = self.cargo.get(good_id, 0)
        
        # Base spread - merchants need profit margin
        base_spread = 0.15  # 15% spread between buy/sell
        
        # Supply pressure: more stock = lower buy prices, higher sell prices
        stock_factor = max(0.5, min(2.0, stock / 10))  # Stock pressure multiplier
        
        # Player inventory pressure: having goods makes selling less favorable
        inventory_pressure = 1.0 + (player_cargo * 0.02)  # 2% penalty per unit held
        
        # Market specialization: cities are better at buying their specialties
        is_specialty = good_id in city.modifiers and city.modifiers[good_id].a_mod < 0
        specialty_bonus = 0.05 if is_specialty else 0
        
        if is_buying:
            # Player buying: pay market premium + spread
            spread_multiplier = 1.0 + base_spread + (1.0 / stock_factor - 1.0) * 0.1
            price.a *= spread_multiplier
            
            # Less favorable if city specializes in this good (they know its value)
            if is_specialty:
                price.a *= 1.02
                price.b += 0.5
        else:
            # Player selling: receive discount from market price
            spread_multiplier = 1.0 - base_spread - specialty_bonus
            
            # Stock pressure: more stock in market = worse sell prices
            spread_multiplier -= (stock_factor - 1.0) * 0.05
            
            # Inventory pressure: having lots makes you desperate seller
            spread_multiplier /= inventory_pressure
            
            price.a *= max(0.7, spread_multiplier)  # Minimum 30% loss protection
            
            # Selling in specialty cities is more favorable
            if is_specialty:
                price.b -= 0.3
        
        # Apply reputation (helps both buying and selling)
        rep_bonus = self.reputation.get("merchant_guild", 0) * -0.15
        price.b += rep_bonus
        
        return price
    
    def can_afford_house(self) -> bool:
        """Check if player can afford the victory house (10000 coins)"""
        house_price = SurrealNumber(10000, 0, 0)
        return self.money >= house_price and not self.owns_house
    
    def purchase_house(self) -> bool:
        """Purchase the victory house"""
        if self.can_afford_house():
            house_price = SurrealNumber(10000, 0, 0)
            self.money = self.money - house_price
            self.owns_house = True
            self.game_completed = True
            return True
        return False
    
    def can_afford(self, price: SurrealNumber) -> bool:
        """Check if player can afford a price"""
        if not price.is_legal():
            return False
        return self.money >= price
    
    def negotiate_price(self, good_id: str, city_id: str, quantity: int, is_buying: bool) -> Optional[SurrealNumber]:
        """Simplified negotiation - in full game this would be interactive"""
        base_price = self.get_price(good_id, city_id, is_buying)
        
        if not base_price.is_legal():
            print(f"❌ Cannot trade {good_id} - requires permit!")
            return None
        
        # Create negotiation cut
        cut = NegotiationCut()
        
        # Player's opening offer
        if is_buying:
            player_offer = base_price * 0.85  # Try to buy lower
            cut.add_offer(player_offer, False)
            merchant_counter = base_price * 1.05
            cut.add_offer(merchant_counter, True)
        else:
            player_offer = base_price * 1.15  # Try to sell higher  
            cut.add_offer(player_offer, True)
            merchant_counter = base_price * 0.95
            cut.add_offer(merchant_counter, False)
        
        # Resolve to simplest price in gap
        final_price = cut.find_simplest_in_gap()
        if final_price is None:
            final_price = base_price
        
        return final_price * quantity

class GameEngine:
    def __init__(self):
        self.state = GameState()
        
    def display_city_screen(self):
        city = self.state.cities[self.state.current_city]
        print(f"\n{'='*60}")
        print(f"🏛️  {city.name.upper()} - Day {self.state.day}")
        print(f"💰 Funds: {self.state.money}")
        print(f"🚢 Cargo: {sum(self.state.cargo.values())}/{self.state.ship.cargo_capacity}")
        print("="*60)
        
        # Show victory condition if in Carthage
        if self.state.current_city == "carthage":
            if self.state.owns_house:
                print("🏠 You own a magnificent house in Carthage!")
            elif self.state.can_afford_house():
                print("💎 VICTORY AVAILABLE: You can afford a house! (Action 8)")
            else:
                house_price = SurrealNumber(10000, 0, 0)
                needed = house_price.a - self.state.money.a
                print(f"🏠 Victory Goal: Buy a house for 10,000 coins (Need {needed:.0f} more)")
        
        # Check for supply refresh
        days_until_refresh = 14 - (self.state.day - self.state.last_supply_refresh_day)
        if days_until_refresh <= 3:
            print(f"📦 Supply caravans arriving in {days_until_refresh} days")
        elif days_until_refresh == 14:
            print("📦 Supply caravans just arrived!")
        
        print("\n📦 MARKET PRICES:")
        print(f"{'Good':<15} {'Stock':<6} {'Buy Price':<25} {'Sell Price':<25} {'Status'}")
        print("-" * 95)
        
        for good_id, stock in city.stock.items():
            if good_id in self.state.goods:
                buy_price = self.state.get_price(good_id, self.state.current_city, True)
                sell_price = self.state.get_price(good_id, self.state.current_city, False)
                
                status = ""
                if not buy_price.is_legal():
                    status = "🚫 RESTRICTED"
                elif stock < 5:
                    status = "⚠️  Low stock"
                elif stock > 25:
                    status = "📈 Well stocked"
                elif good_id in self.state.cargo and self.state.cargo[good_id] > 10:
                    status = "📦 You hold many"
                    
                # Show spread warning for expensive goods
                spread_pct = ((buy_price.a - sell_price.a) / buy_price.a) * 100
                if spread_pct > 20:
                    status += " 💸 High spread"
                    
                print(f"{self.state.goods[good_id].name:<15} {stock:<6} {str(buy_price):<25} {str(sell_price):<25} {status}")
        
        # Show market analysis
        print(f"\n💡 Market Analysis:")
        print(f"   • Supply caravans arrive every 2 weeks (14 days)")
        print(f"   • Next resupply in {days_until_refresh} days")
        print(f"   • Cities produce more of their specialty goods")
        print(f"   • Higher stock = worse sell prices, better buy prices")
    
    def display_available_actions(self):
        print("\n🎯 Available Actions:")
        print("1. 🛒 Buy goods")
        print("2. 💰 Sell goods") 
        print("3. ⛵ Travel to another city")
        print("4. 🏪 Visit shipyard")
        print("5. 🍺 Visit tavern (news & rumors)")
        print("6. 📊 View cargo")
        print("7. 📈 View statistics")
        
        # Special actions based on location and status
        if self.state.current_city == "carthage" and not self.state.owns_house:
            if self.state.can_afford_house():
                print("8. 🏠 🎉 BUY HOUSE - ACHIEVE VICTORY! (10,000 coins)")
            else:
                print("8. 🏠 Buy house (10,000 coins) - Not enough money")
        
        print("9. ❌ Quit game")
    
    def buy_goods(self):
        city = self.state.cities[self.state.current_city]
        available_goods = [(gid, stock) for gid, stock in city.stock.items() 
                          if gid in self.state.goods and stock > 0]
        
        if not available_goods:
            print("❌ No goods available for purchase!")
            return
        
        print("\n🛒 Available Goods:")
        for i, (good_id, stock) in enumerate(available_goods, 1):
            good = self.state.goods[good_id]
            price = self.state.get_price(good_id, self.state.current_city, True)
            status = "" if price.is_legal() else " [RESTRICTED]"
            print(f"{i}. {good.name} - Stock: {stock} - Price: {price}{status}")
        
        try:
            choice = int(input("\nSelect good (number): ")) - 1
            if 0 <= choice < len(available_goods):
                good_id, max_stock = available_goods[choice]
                quantity = int(input(f"Quantity (max {max_stock}): "))
                
                if 1 <= quantity <= max_stock:
                    total_price = self.state.negotiate_price(good_id, self.state.current_city, quantity, True)
                    
                    if total_price and self.state.can_afford(total_price):
                        # Execute purchase
                        self.state.money = self.state.money - total_price
                        self.state.cargo[good_id] = self.state.cargo.get(good_id, 0) + quantity
                        city.stock[good_id] -= quantity
                        
                        # Update statistics
                        self.state.stats["total_trades"] += 1
                        self.state.stats["goods_bought"][good_id] = self.state.stats["goods_bought"].get(good_id, 0) + quantity
                        self.state.stats["total_spent"] = self.state.stats["total_spent"] + total_price
                        
                        print(f"✅ Purchased {quantity}x {self.state.goods[good_id].name} for {total_price}")
                    else:
                        print("❌ Cannot afford or trade restricted!")
                else:
                    print("❌ Invalid quantity!")
        except ValueError:
            print("❌ Invalid input!")
    
    def sell_goods(self):
        if not self.state.cargo:
            print("❌ No goods to sell!")
            return
        
        print("\n💰 Your Cargo:")
        cargo_items = list(self.state.cargo.items())
        for i, (good_id, quantity) in enumerate(cargo_items, 1):
            price = self.state.get_price(good_id, self.state.current_city, False)
            print(f"{i}. {self.state.goods[good_id].name} - Quantity: {quantity} - Price each: {price}")
        
        try:
            choice = int(input("\nSelect good to sell (number): ")) - 1
            if 0 <= choice < len(cargo_items):
                good_id, max_quantity = cargo_items[choice]
                quantity = int(input(f"Quantity to sell (max {max_quantity}): "))
                
                if 1 <= quantity <= max_quantity:
                    total_price = self.state.negotiate_price(good_id, self.state.current_city, quantity, False)
                    
                    if total_price:
                        # Execute sale
                        self.state.money = self.state.money + total_price
                        self.state.cargo[good_id] -= quantity
                        if self.state.cargo[good_id] == 0:
                            del self.state.cargo[good_id]
                        
                        city = self.state.cities[self.state.current_city]
                        city.stock[good_id] = city.stock.get(good_id, 0) + quantity
                        
                        # Update statistics
                        self.state.stats["total_trades"] += 1
                        self.state.stats["goods_sold"][good_id] = self.state.stats["goods_sold"].get(good_id, 0) + quantity
                        self.state.stats["total_earned"] = self.state.stats["total_earned"] + total_price
                        
                        print(f"✅ Sold {quantity}x {self.state.goods[good_id].name} for {total_price}")
                    else:
                        print("❌ Cannot complete sale!")
        except ValueError:
            print("❌ Invalid input!")
    
    def travel(self):
        available_routes = [r for r in self.state.routes if r.from_city == self.state.current_city]
        
        if not available_routes:
            print("❌ No routes available!")
            return
        
        print("\n⛵ Available Destinations:")
        for i, route in enumerate(available_routes, 1):
            dest_city = self.state.cities[route.to_city]
            print(f"{i}. {dest_city.name} - {route.min_days}-{route.max_days} days - Risk: {route.base_risk:.0%}")
        
        try:
            choice = int(input("\nSelect destination (number): ")) - 1
            if 0 <= choice < len(available_routes):
                route = available_routes[choice]
                travel_time = route.travel_time()
                
                # Simple travel resolution
                self.state.day += travel_time
                self.state.current_city = route.to_city
                
                # Update statistics
                self.state.stats["cities_visited"].add(route.to_city)
                self.state.stats["routes_traveled"] += 1
                
                # Check for supply refresh after travel
                refresh_occurred = self.state.check_supply_refresh()
                if refresh_occurred:
                    refresh_messages = self.state.refresh_city_supplies()
                    print(f"\n📦 SUPPLY CARAVANS ARRIVED! (Day {self.state.day})")
                    print("New supplies have reached the markets:")
                    for message in refresh_messages[-6:]:  # Show last 6 messages to avoid spam
                        print(message)
                    if len(refresh_messages) > 6:
                        print(f"   ...and {len(refresh_messages) - 6} other supply updates")
                
                # Random event chance
                if random.random() < route.base_risk:
                    self._handle_travel_event()
                
                print(f"⛵ Arrived in {self.state.cities[self.state.current_city].name} after {travel_time} days")
        except ValueError:
            print("❌ Invalid input!")
    
    def _handle_travel_event(self):
        """Handle random events during travel"""
        events = [
            "🏴‍☠️ Pirates demand tribute! Lost 50 coins.",
            "⛈️ Storm delays journey! Crew morale slightly decreased.", 
            "🐟 Favorable winds! Arrived ahead of schedule.",
            "🗣️ Met another trader with valuable information!"
        ]
        
        event = random.choice(events)
        print(f"\n🎲 EVENT: {event}")
        
        # Update statistics
        self.state.stats["events_encountered"] += 1
        
        # Apply simple consequences
        if "Pirates" in event:
            self.state.money = self.state.money - 50
        elif "morale" in event:
            self.state.ship.crew_morale *= 0.9
    
    def view_cargo(self):
        if not self.state.cargo:
            print("📦 Cargo hold is empty!")
            return
        
        print(f"\n📦 CARGO ({sum(self.state.cargo.values())}/{self.state.ship.cargo_capacity}):")
        print("-" * 40)
        total_value = SurrealNumber()
        
        for good_id, quantity in self.state.cargo.items():
            good = self.state.goods[good_id]
            est_value = self.state.get_price(good_id, self.state.current_city, False) * quantity
            total_value = total_value + est_value
            print(f"{good.name}: {quantity} units (Est. value: {est_value})")
        
        print(f"\nTotal estimated value: {total_value}")
    
    def view_statistics(self):
        """Display comprehensive game statistics"""
        stats = self.state.stats
        
        print(f"\n📈 TRADING STATISTICS - Day {self.state.day}")
        print("=" * 50)
        
        # Financial overview
        current_worth = self.state.get_net_worth()
        profit_loss = SurrealNumber(current_worth.a - self.state.start_money.a, 
                                  current_worth.b - self.state.start_money.b, 0)
        
        print(f"💰 Financial Status:")
        print(f"   Starting capital: {self.state.start_money}")
        print(f"   Current cash: {self.state.money}")
        print(f"   Net worth: {current_worth}")
        print(f"   Total profit/loss: {profit_loss}")
        
        if self.state.owns_house:
            print(f"   🏠 House value: 10,000 (VICTORY ACHIEVED!)")
        
        # Trading activity
        print(f"\n📊 Trading Activity:")
        print(f"   Total trades: {stats['total_trades']}")
        print(f"   Total spent: {stats['total_spent']}")
        print(f"   Total earned: {stats['total_earned']}")
        
        # Goods breakdown
        if stats['goods_bought']:
            print(f"\n📦 Goods Purchased:")
            for good_id, qty in stats['goods_bought'].items():
                good_name = self.state.goods[good_id].name
                print(f"   {good_name}: {qty} units")
        
        if stats['goods_sold']:
            print(f"\n💰 Goods Sold:")
            for good_id, qty in stats['goods_sold'].items():
                good_name = self.state.goods[good_id].name
                print(f"   {good_name}: {qty} units")
        
        # Travel stats
        print(f"\n🗺️ Travel Statistics:")
        print(f"   Cities visited: {len(stats['cities_visited'])}")
        visited_names = [self.state.cities[city_id].name for city_id in stats['cities_visited']]
        print(f"   Locations: {', '.join(visited_names)}")
        print(f"   Routes traveled: {stats['routes_traveled']}")
        print(f"   Events encountered: {stats['events_encountered']}")
        print(f"   Supply refreshes witnessed: {stats['supply_refreshes']}")
        
        # Supply refresh info
        days_until_refresh = 14 - (self.state.day - self.state.last_supply_refresh_day)
        print(f"\n📦 Supply Information:")
        print(f"   Last supply refresh: Day {self.state.last_supply_refresh_day}")
        print(f"   Next refresh in: {days_until_refresh} days")
        print(f"   Cities restock specialty goods every 2 weeks")
        
        # Victory progress
        if not self.state.owns_house:
            house_price = 10000
            progress = (current_worth.a / house_price) * 100
            print(f"\n🏠 Victory Progress:")
            print(f"   House goal: {house_price} coins")
            print(f"   Current progress: {progress:.1f}%")
            if progress >= 100:
                print("   🎉 VICTORY AVAILABLE! Return to Carthage to buy your house!")
    
    def buy_house(self):
        """Handle house purchase and victory"""
        if self.state.current_city != "carthage":
            print("❌ Houses are only available in Carthage!")
            return
        
        if self.state.owns_house:
            print("🏠 You already own a house in Carthage!")
            return
        
        if not self.state.can_afford_house():
            house_price = 10000
            needed = house_price - self.state.money.a
            print(f"❌ You need {needed:.0f} more coins to buy a house!")
            return
        
        # Purchase the house!
        if self.state.purchase_house():
            self.show_victory_screen()
    
    def show_victory_screen(self):
        """Display the final victory screen with comprehensive results"""
        print("\n" + "="*70)
        print("🎉🏠 VICTORY ACHIEVED! 🏠🎉")
        print("You have purchased a magnificent house in Carthage!")
        print("="*70)
        
        # Time to completion
        print(f"\n⏰ COMPLETION TIME: {self.state.day} days")
        
        # Final financial summary
        final_worth = self.state.get_net_worth() + SurrealNumber(10000, 0, 0)  # Add house value back
        total_profit = final_worth.a - self.state.start_money.a
        
        print(f"\n💎 FINAL FINANCIAL REPORT:")
        print(f"   Starting capital: {self.state.start_money.a:.0f} coins")
        print(f"   House purchase: 10,000 coins")
        print(f"   Remaining cash: {self.state.money.a:.0f} coins") 
        print(f"   Final net worth: {final_worth.a:.0f} coins")
        print(f"   Total profit: {total_profit:.0f} coins ({((total_profit/self.state.start_money.a)*100):.1f}%)")
        
        # Trading efficiency
        stats = self.state.stats
        if stats['total_trades'] > 0:
            avg_profit_per_trade = total_profit / stats['total_trades']
            avg_profit_per_day = total_profit / self.state.day
            
            print(f"\n📊 TRADING EFFICIENCY:")
            print(f"   Total trades: {stats['total_trades']}")
            print(f"   Average profit per trade: {avg_profit_per_trade:.1f} coins")
            print(f"   Average profit per day: {avg_profit_per_day:.1f} coins")
        
        # Goods traded summary
        total_bought = sum(stats['goods_bought'].values()) if stats['goods_bought'] else 0
        total_sold = sum(stats['goods_sold'].values()) if stats['goods_sold'] else 0
        
        print(f"\n📦 TRADE VOLUME:")
        print(f"   Total goods purchased: {total_bought} units")
        print(f"   Total goods sold: {total_sold} units")
        print(f"   Net goods traded: {total_bought + total_sold} units")
        
        # Most traded goods
        if stats['goods_bought']:
            best_buy = max(stats['goods_bought'].items(), key=lambda x: x[1])
            print(f"   Most purchased: {self.state.goods[best_buy[0]].name} ({best_buy[1]} units)")
        
        if stats['goods_sold']:
            best_sell = max(stats['goods_sold'].items(), key=lambda x: x[1])
            print(f"   Most sold: {self.state.goods[best_sell[0]].name} ({best_sell[1]} units)")
        
        # Travel achievements
        print(f"\n🗺️ EXPLORATION ACHIEVEMENTS:")
        print(f"   Cities discovered: {len(stats['cities_visited'])}/3")
        visited_names = [self.state.cities[city_id].name for city_id in stats['cities_visited']]
        print(f"   Cities visited: {', '.join(visited_names)}")
        print(f"   Routes traveled: {stats['routes_traveled']}")
        print(f"   Adventures survived: {stats['events_encountered']}")
        
        # Performance rating
        print(f"\n⭐ PERFORMANCE RATING:")
        score = 0
        if self.state.day <= 30:
            score += 3
            print("   🏃‍♂️ Speed Merchant: Completed in 30 days or less (+3 ⭐)")
        elif self.state.day <= 60:
            score += 2
            print("   ⏰ Efficient Trader: Completed in 60 days or less (+2 ⭐)")
        else:
            score += 1
            print("   🐌 Steady Progress: Took your time (+1 ⭐)")
        
        if total_profit > 15000:
            score += 3
            print("   💎 Master Merchant: Over 15,000 profit (+3 ⭐)")
        elif total_profit > 10000:
            score += 2
            print("   💰 Successful Trader: Over 10,000 profit (+2 ⭐)")
        else:
            score += 1
            print("   📈 Profitable Venture: Made a profit (+1 ⭐)")
        
        if len(stats['cities_visited']) == 3:
            score += 2
            print("   🌍 Explorer: Visited all cities (+2 ⭐)")
        
        if stats['events_encountered'] >= 5:
            score += 1
            print("   ⚔️ Adventurer: Survived many events (+1 ⭐)")
        
        print(f"\n   🏆 FINAL SCORE: {score}/10 ⭐")
        
        if score >= 8:
            print("   🎖️ LEGENDARY PHOENICIAN MERCHANT!")
        elif score >= 6:
            print("   🥉 EXPERT TRADER!")
        elif score >= 4:
            print("   🥈 SKILLED MERCHANT!")
        else:
            print("   🥉 NOVICE TRADER - Keep practicing!")
        
        print("\n🌊 Thank you for playing Surreal Phoenicians! 🌊")
        print("=" * 70)
    
    def run_game_loop(self):
        print("🌊 Welcome to Surreal Phoenicians! 🌊")
        print("You are a trader in the ancient Mediterranean...")
        
        while True:
            # Check for victory condition
            if self.state.game_completed:
                break
                
            self.display_city_screen()
            self.display_available_actions()
            
            try:
                max_action = 9 if (self.state.current_city == "carthage" and not self.state.owns_house) else 9
                action = int(input(f"\nChoose action (1-{max_action}): "))
                
                if action == 1:
                    self.buy_goods()
                elif action == 2:
                    self.sell_goods()
                elif action == 3:
                    self.travel()
                elif action == 4:
                    print("🔧 Shipyard coming soon!")
                elif action == 5:
                    print("🍺 Tavern coming soon!")
                elif action == 6:
                    self.view_cargo()
                elif action == 7:
                    self.view_statistics()
                elif action == 8 and self.state.current_city == "carthage" and not self.state.owns_house:
                    self.buy_house()
                elif action == 9:
                    print("⚓ Thanks for playing Surreal Phoenicians!")
                    break
                else:
                    print("❌ Invalid choice!")
                    
                if not self.state.game_completed:
                    input("\nPress Enter to continue...")
                    
            except ValueError:
                print("❌ Invalid input!")
            except KeyboardInterrupt:
                print("\n⚓ Game ended by player.")
                break

if __name__ == "__main__":
    # Demo of surreal number arithmetic
    print("🔢 Surreal Number Demo:")
    price1 = SurrealNumber(120, -1, 0)  # Glass price with reputation bonus
    price2 = SurrealNumber(220, -3, 1)  # Purple dye with embargo
    
    print(f"Glass price: {price1}")
    print(f"Purple dye (embargoed): {price2}")
    print(f"Sum: {price1 + price2}")
    print(f"Glass is legal: {price1.is_legal()}")
    print(f"Dye is legal: {price2.is_legal()}")
    print(f"Dye with permit: {price2.clear_omega()}")
    
    print(f"\nComparison: Glass < Dye? {price1 < price2}")
    print(f"Glass < Permitted Dye? {price1 < price2.clear_omega()}")
    
    print("\n" + "="*50)
    
    # Run the game
    game = GameEngine()
    game.run_game_loop()