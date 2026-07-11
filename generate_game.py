import random

def generate_dominion_sql():
    # Core IDs
    C_COPPER = "B027"
    C_SILVER = "B028"
    C_GOLD = "B029"
    C_ESTATE = "B030"
    C_DUCHY = "B031"
    C_PROVINCE = "B032"

    K_VILLAGE = "B024"
    K_SMITHY = "B022"
    K_MILITIA = "B014"
    K_MARKET = "B012"
    K_CELLAR = "B004"
    K_WITCH = "B025"
    K_FESTIVAL = "B009"
    K_LABORATORY = "B010"
    K_MOAT = "B015"
    K_WORKSHOP = "B026"

    cards_db = {
        C_COPPER: {"val": 1, "vp": 0, "type": "Treasure"},
        C_SILVER: {"val": 2, "vp": 0, "type": "Treasure"},
        C_GOLD: {"val": 3, "vp": 0, "type": "Treasure"},
        C_ESTATE: {"val": 0, "vp": 1, "type": "Victory"},
        C_DUCHY: {"val": 0, "vp": 3, "type": "Victory"},
        C_PROVINCE: {"val": 0, "vp": 6, "type": "Victory"},
        K_VILLAGE: {"val": 0, "vp": 0, "type": "Action", "draw": 1, "actions": 2},
        K_SMITHY: {"val": 0, "vp": 0, "type": "Action", "draw": 3, "actions": 0},
        K_MILITIA: {"val": 2, "vp": 0, "type": "Action", "draw": 0, "actions": 0},
        K_MARKET: {"val": 1, "vp": 0, "type": "Action", "draw": 1, "actions": 1},
        K_CELLAR: {"val": 0, "vp": 0, "type": "Action", "draw": 0, "actions": 1},
        K_WITCH: {"val": 0, "vp": 0, "type": "Action", "draw": 2, "actions": 0},
        K_FESTIVAL: {"val": 2, "vp": 0, "type": "Action", "draw": 0, "actions": 2},
        K_LABORATORY: {"val": 0, "vp": 0, "type": "Action", "draw": 2, "actions": 1},
        K_MOAT: {"val": 0, "vp": 0, "type": "Action", "draw": 2, "actions": 0},
        K_WORKSHOP: {"val": 0, "vp": 0, "type": "Action", "draw": 0, "actions": 0}
    }

    supply = {
        C_PROVINCE: 12, C_DUCHY: 12, C_ESTATE: 12, C_GOLD: 30, C_SILVER: 40, C_COPPER: 60,
        K_VILLAGE: 10, K_SMITHY: 10, K_MILITIA: 10, K_MARKET: 10, K_CELLAR: 10,
        K_WITCH: 10, K_FESTIVAL: 10, K_LABORATORY: 10, K_MOAT: 10, K_WORKSHOP: 10
    }

    k_cards = [K_VILLAGE, K_SMITHY, K_MILITIA, K_MARKET, K_CELLAR, K_WITCH, K_FESTIVAL, K_LABORATORY, K_MOAT, K_WORKSHOP]

    players = [
        {"pid": "P001", "strat": "militia"},
        {"pid": "P002", "strat": "smithy"},
        {"pid": "P003", "strat": "village"},
        {"pid": "P004", "strat": "market"}
    ]

    random.seed(101) # Keeps the game deterministic if you run it multiple times

    for p in players:
        p["deck"] = [C_COPPER]*7 + [C_ESTATE]*3
        random.shuffle(p["deck"])
        p["discard"] = []
        p["hand"] = []

    def draw_cards(p, num):
        drawn = []
        for _ in range(num):
            if not p["deck"]:
                if not p["discard"]: break
                p["deck"] = p["discard"]
                p["discard"] = []
                random.shuffle(p["deck"])
            card = p["deck"].pop(0)
            p["hand"].append(card)
            drawn.append(card)
        return drawn

    for p in players: draw_cards(p, 5)

    events = []
    starting_hands = []
    turn = 1
    game_over = False

    while not game_over and turn <= 40:
        for p in players:
            if supply[C_PROVINCE] == 0:
                game_over = True
                break
                
            # 1. Log starting hand snapshot
            counts = {}
            for c in p["hand"]: counts[c] = counts.get(c, 0) + 1
            for c, qty in counts.items():
                starting_hands.append((p["pid"], turn, c, qty))
                
            actions_available = 1
            action_money = 0
            played_cards = []
            
            # 2. ACTIONS PHASE
            while actions_available > 0:
                action_cards = [c for c in p["hand"] if cards_db[c]["type"] == "Action"]
                if not action_cards: break
                
                c = action_cards[0]
                p["hand"].remove(c)
                played_cards.append(c)
                events.append((p["pid"], turn, "PLAY", c, 1))
                
                actions_available -= 1
                actions_available += cards_db[c].get("actions", 0)
                action_money += cards_db[c].get("val", 0)
                
                draw_amt = cards_db[c].get("draw", 0)
                if draw_amt > 0:
                    drawn_cards = draw_cards(p, draw_amt)
                    dc_counts = {}
                    for dc in drawn_cards: dc_counts[dc] = dc_counts.get(dc, 0) + 1
                    for dc, qty in dc_counts.items():
                        events.append((p["pid"], turn, "DRAW", dc, qty))
                        
                if c == K_MILITIA:
                    for op in players:
                        if op["pid"] != p["pid"]:
                            while len(op["hand"]) > 3:
                                # Simple logic: Drop worst cards first
                                if C_ESTATE in op["hand"]: drop = C_ESTATE
                                elif C_DUCHY in op["hand"]: drop = C_DUCHY
                                elif C_PROVINCE in op["hand"]: drop = C_PROVINCE
                                else: drop = op["hand"][0]
                                op["hand"].remove(drop)
                                op["discard"].append(drop)
                                events.append((op["pid"], turn, "DISCARD", drop, 1))
                                
            # 3. TREASURE PHASE
            treasures = [c for c in p["hand"] if cards_db[c]["type"] == "Treasure"]
            t_counts = {}
            for t_card in treasures:
                p["hand"].remove(t_card)
                played_cards.append(t_card)
                t_counts[t_card] = t_counts.get(t_card, 0) + 1
            for t_card, qty in t_counts.items():
                events.append((p["pid"], turn, "PLAY", t_card, qty))
                
            money = sum(cards_db[tc]["val"] * qty for tc, qty in t_counts.items()) + action_money
            
            # 4. BUY PHASE
            buy = None
            if money >= 8 and supply[C_PROVINCE] > 0: buy = C_PROVINCE
            elif money >= 6 and supply[C_GOLD] > 0: buy = C_GOLD
            elif money >= 5 and supply[C_PROVINCE] <= 5 and supply[C_DUCHY] > 0: buy = C_DUCHY
            elif money >= 5 and supply[K_MARKET] > 0 and p["strat"] == "market": buy = K_MARKET
            elif money >= 5 and supply[K_WITCH] > 0: buy = K_WITCH
            elif money >= 4 and supply[K_MILITIA] > 0 and p["strat"] == "militia": buy = K_MILITIA
            elif money >= 4 and supply[K_SMITHY] > 0 and p["strat"] == "smithy": buy = K_SMITHY
            elif money >= 3 and supply[K_VILLAGE] > 0 and p["strat"] == "village": buy = K_VILLAGE
            elif money >= 3 and supply[C_SILVER] > 0: buy = C_SILVER
                
            if buy:
                supply[buy] -= 1
                p["discard"].append(buy)
                events.append((p["pid"], turn, "BUY", buy, 1))
            else:
                events.append((p["pid"], turn, "PASS", "NULL", 0))
                
            # 5. CLEANUP PHASE
            cleanup_counts = {}
            for c in p["hand"]:
                cleanup_counts[c] = cleanup_counts.get(c, 0) + 1
            for c, qty in cleanup_counts.items():
                events.append((p["pid"], turn, "CLEANUP", c, qty))
                
            p["discard"].extend(p["hand"] + played_cards)
            p["hand"] = []
            draw_cards(p, 5)
            
        if game_over:
            break
        turn += 1

    # Format the entire game into SQL
    sql = "-- ====================================================================\n"
    sql += f"-- 1. CREATE NEW GAME (G-300) & KINGDOM (Ended naturally on Turn {turn-1})\n"
    sql += "-- ====================================================================\n"
    sql += "INSERT INTO Games (game_id, expansion_set, notes) VALUES \n('G-300', 'Base 2E', 'Full Semantic Game: PLAY, DRAW, DISCARD, BUY, CLEANUP');\n\n"

    # Calculate final scores
    scores = []
    for p in players:
        all_c = p["deck"] + p["discard"] + p["hand"]
        vp = sum(cards_db.get(c, {}).get("vp", 0) for c in all_c)
        scores.append((p["pid"], vp))
    
    scores.sort(key=lambda x: x[1], reverse=True)
    
    sql += "INSERT INTO GamePlayers (game_id, player_id, placement, score) VALUES\n"
    for i, (pid, vp) in enumerate(scores):
        sql += f"('G-300', '{pid}', {i+1}, {vp}){',' if i < 3 else ';'}\n"
    sql += "\n"

    sql += "INSERT INTO GameKingdomCards (game_id, card_id) VALUES\n"
    sql += ",\n".join([f"('G-300', '{c}')" for c in k_cards]) + ";\n\n"

    sql += "-- ====================================================================\n"
    sql += "-- 2. TURN STARTING HANDS\n"
    sql += "-- ====================================================================\n"
    sql += "INSERT INTO TurnStartingHands (game_id, player_id, turn_number, card_id, quantity) VALUES\n"
    hand_vals = []
    for t in range(1, turn):
        for p in ["P001", "P002", "P003", "P004"]:
            for h in starting_hands:
                if h[1] == t and h[0] == p:
                    hand_vals.append(f"('G-300', '{h[0]}', {h[1]}, '{h[2]}', {h[3]})")
    sql += ",\n".join(hand_vals) + ";\n\n"

    sql += "-- ====================================================================\n"
    sql += "-- 3. GAME EVENTS (PLAY -> DRAW -> BUY -> CLEANUP/DISCARD)\n"
    sql += "-- ====================================================================\n"
    sql += "INSERT INTO GameEvents (game_id, player_id, turn_number, action_type, card_id, quantity) VALUES\n"
    ev_vals = []
    for t in range(1, turn):
        for p in ["P001", "P002", "P003", "P004"]:
            for e in events:
                if e[1] == t and e[0] == p:
                    c_id = f"'{e[3]}'" if e[3] != 'NULL' else 'NULL'
                    ev_vals.append(f"('G-300', '{e[0]}', {e[1]}, '{e[2]}', {c_id}, {e[4]})")
    sql += ",\n".join(ev_vals) + ";\n\n"

    sql += "-- ====================================================================\n"
    sql += "-- 4. FINAL DECK COMPOSITION\n"
    sql += "-- ====================================================================\n"
    sql += "INSERT INTO FinalDeckComposition (game_id, player_id, card_id, count) VALUES\n"
    deck_vals = []
    for p in players:
        all_cards = p["deck"] + p["discard"] + p["hand"]
        counts = {}
        for c in all_cards: counts[c] = counts.get(c, 0) + 1
        for c, count in counts.items():
            deck_vals.append(f"('G-300', '{p['pid']}', '{c}', {count})")
    sql += ",\n".join(deck_vals) + ";\n\n"
    
    sql += f"UPDATE Games SET winner_id = '{scores[0][0]}', winning_score = {scores[0][1]} WHERE game_id = 'G-300';\n"

    with open("G-300_full_game.sql", "w") as f:
        f.write(sql)
    
    print(f"✅ Game finished naturally on Turn {turn-1}!")
    print(f"🏆 Winner: {scores[0][0]} with {scores[0][1]} VP")
    print(f"💾 Full SQL script written to 'G-300_full_game.sql' in your current folder.")

if __name__ == "__main__":
    generate_dominion_sql()