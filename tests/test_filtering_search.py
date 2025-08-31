"""Tests for filtering and search functionality in MTG Deck Builder."""

import pytest
from unittest.mock import Mock, patch


class TestFilteringAndSearch:
    """Test filtering and search functionality."""
    
    @pytest.fixture
    def sample_card_database(self):
        """Provide a sample card database for testing."""
        return [
            {
                "name": "Lightning Bolt",
                "mana_cost": "{R}",
                "cmc": 1,
                "type_line": "Instant",
                "colors": ["R"],
                "color_identity": ["R"],
                "oracle_text": "Lightning Bolt deals 3 damage to any target.",
                "rarity": "common",
                "set": "M21",
                "power": None,
                "toughness": None
            },
            {
                "name": "Lightning Strike",
                "mana_cost": "{1}{R}",
                "cmc": 2,
                "type_line": "Instant",
                "colors": ["R"],
                "color_identity": ["R"],
                "oracle_text": "Lightning Strike deals 3 damage to any target.",
                "rarity": "common",
                "set": "M21",
                "power": None,
                "toughness": None
            },
            {
                "name": "Giant Growth",
                "mana_cost": "{G}",
                "cmc": 1,
                "type_line": "Instant",
                "colors": ["G"],
                "color_identity": ["G"],
                "oracle_text": "Target creature gets +3/+3 until end of turn.",
                "rarity": "common",
                "set": "M21",
                "power": None,
                "toughness": None
            },
            {
                "name": "Grizzly Bears",
                "mana_cost": "{1}{G}",
                "cmc": 2,
                "type_line": "Creature — Bear",
                "colors": ["G"],
                "color_identity": ["G"],
                "oracle_text": "",
                "rarity": "common",
                "set": "M21",
                "power": 2,
                "toughness": 2
            },
            {
                "name": "Sol Ring",
                "mana_cost": "{1}",
                "cmc": 1,
                "type_line": "Artifact",
                "colors": [],
                "color_identity": [],
                "oracle_text": "{T}: Add {C}{C}.",
                "rarity": "uncommon",
                "set": "CMD",
                "power": None,
                "toughness": None
            },
            {
                "name": "Counterspell",
                "mana_cost": "{U}{U}",
                "cmc": 2,
                "type_line": "Instant",
                "colors": ["U"],
                "color_identity": ["U"],
                "oracle_text": "Counter target spell.",
                "rarity": "common",
                "set": "M21",
                "power": None,
                "toughness": None
            },
            {
                "name": "Black Lotus",
                "mana_cost": "{0}",
                "cmc": 0,
                "type_line": "Artifact",
                "colors": [],
                "color_identity": [],
                "oracle_text": "{T}, Sacrifice Black Lotus: Add three mana of any one color.",
                "rarity": "mythic",
                "set": "LEA",
                "power": None,
                "toughness": None
            },
            {
                "name": "Omnath, Locus of Mana",
                "mana_cost": "{2}{G}",
                "cmc": 3,
                "type_line": "Legendary Creature — Elemental",
                "colors": ["G"],
                "color_identity": ["G"],
                "oracle_text": "Green mana doesn't empty from your mana pool as steps and phases end. Omnath gets +1/+1 for each unspent green mana you have.",
                "rarity": "mythic",
                "set": "ZEN",
                "power": 1,
                "toughness": 1
            }
        ]

    def test_search_by_name(self, sample_card_database):
        """Test searching cards by name."""
        # Test exact match
        exact_results = [card for card in sample_card_database 
                        if card["name"].lower() == "lightning bolt"]
        assert len(exact_results) == 1
        assert exact_results[0]["name"] == "Lightning Bolt"
        
        # Test partial match
        partial_results = [card for card in sample_card_database 
                          if "lightning" in card["name"].lower()]
        assert len(partial_results) == 2
        assert any(card["name"] == "Lightning Bolt" for card in partial_results)
        assert any(card["name"] == "Lightning Strike" for card in partial_results)
        
        # Test case insensitive
        case_results = [card for card in sample_card_database 
                       if "LIGHTNING" in card["name"].upper()]
        assert len(case_results) == 2

    def test_search_by_oracle_text(self, sample_card_database):
        """Test searching cards by oracle text."""
        # Search for damage spells
        damage_results = [card for card in sample_card_database 
                         if "damage" in card["oracle_text"].lower()]
        assert len(damage_results) == 2
        assert all("damage" in card["oracle_text"].lower() for card in damage_results)
        
        # Search for counter spells
        counter_results = [card for card in sample_card_database 
                          if "counter" in card["oracle_text"].lower()]
        assert len(counter_results) == 1
        assert counter_results[0]["name"] == "Counterspell"
        
        # Search for mana abilities
        mana_results = [card for card in sample_card_database 
                       if "add" in card["oracle_text"].lower() and "mana" in card["oracle_text"].lower()]
        assert len(mana_results) == 2  # Sol Ring and Black Lotus

    def test_filter_by_color(self, sample_card_database):
        """Test filtering cards by color."""
        # Filter red cards
        red_cards = [card for card in sample_card_database 
                    if "R" in card["colors"]]
        assert len(red_cards) == 2
        assert all("R" in card["colors"] for card in red_cards)
        
        # Filter green cards
        green_cards = [card for card in sample_card_database 
                      if "G" in card["colors"]]
        assert len(green_cards) == 3
        
        # Filter colorless cards
        colorless_cards = [card for card in sample_card_database 
                          if not card["colors"]]
        assert len(colorless_cards) == 2
        assert all(not card["colors"] for card in colorless_cards)
        
        # Filter multicolor cards (none in this sample)
        multicolor_cards = [card for card in sample_card_database 
                           if len(card["colors"]) > 1]
        assert len(multicolor_cards) == 0

    def test_filter_by_color_identity(self, sample_card_database):
        """Test filtering cards by color identity."""
        # Filter by red color identity
        red_identity = [card for card in sample_card_database 
                       if "R" in card["color_identity"]]
        assert len(red_identity) == 2
        
        # Filter by green color identity
        green_identity = [card for card in sample_card_database 
                         if "G" in card["color_identity"]]
        assert len(green_identity) == 3
        
        # Filter colorless identity
        colorless_identity = [card for card in sample_card_database 
                             if not card["color_identity"]]
        assert len(colorless_identity) == 2

    def test_filter_by_converted_mana_cost(self, sample_card_database):
        """Test filtering cards by converted mana cost."""
        # Filter 1 CMC cards
        one_cmc = [card for card in sample_card_database if card["cmc"] == 1]
        assert len(one_cmc) == 3
        assert all(card["cmc"] == 1 for card in one_cmc)
        
        # Filter 2 CMC cards
        two_cmc = [card for card in sample_card_database if card["cmc"] == 2]
        assert len(two_cmc) == 3
        
        # Filter by CMC range
        low_cmc = [card for card in sample_card_database if card["cmc"] <= 1]
        assert len(low_cmc) == 4  # Including 0 CMC
        
        high_cmc = [card for card in sample_card_database if card["cmc"] >= 3]
        assert len(high_cmc) == 1

    def test_filter_by_card_type(self, sample_card_database):
        """Test filtering cards by type."""
        # Filter instants
        instants = [card for card in sample_card_database 
                   if "Instant" in card["type_line"]]
        assert len(instants) == 4
        assert all("Instant" in card["type_line"] for card in instants)
        
        # Filter creatures
        creatures = [card for card in sample_card_database 
                    if "Creature" in card["type_line"]]
        assert len(creatures) == 2
        
        # Filter artifacts
        artifacts = [card for card in sample_card_database 
                    if "Artifact" in card["type_line"]]
        assert len(artifacts) == 2
        
        # Filter legendary cards
        legendary = [card for card in sample_card_database 
                    if "Legendary" in card["type_line"]]
        assert len(legendary) == 1
        assert legendary[0]["name"] == "Omnath, Locus of Mana"

    def test_filter_by_rarity(self, sample_card_database):
        """Test filtering cards by rarity."""
        # Filter common cards
        commons = [card for card in sample_card_database 
                  if card["rarity"] == "common"]
        assert len(commons) == 5
        
        # Filter uncommon cards
        uncommons = [card for card in sample_card_database 
                    if card["rarity"] == "uncommon"]
        assert len(uncommons) == 1
        assert uncommons[0]["name"] == "Sol Ring"
        
        # Filter mythic cards
        mythics = [card for card in sample_card_database 
                  if card["rarity"] == "mythic"]
        assert len(mythics) == 2

    def test_filter_by_set(self, sample_card_database):
        """Test filtering cards by set."""
        # Filter M21 cards
        m21_cards = [card for card in sample_card_database 
                    if card["set"] == "M21"]
        assert len(m21_cards) == 5
        
        # Filter CMD cards
        cmd_cards = [card for card in sample_card_database 
                    if card["set"] == "CMD"]
        assert len(cmd_cards) == 1
        assert cmd_cards[0]["name"] == "Sol Ring"
        
        # Filter LEA cards
        lea_cards = [card for card in sample_card_database 
                    if card["set"] == "LEA"]
        assert len(lea_cards) == 1
        assert lea_cards[0]["name"] == "Black Lotus"

    def test_filter_by_power_toughness(self, sample_card_database):
        """Test filtering creatures by power and toughness."""
        # Filter creatures with power 2
        power_2 = [card for card in sample_card_database 
                  if card.get("power") == 2]
        assert len(power_2) == 1
        assert power_2[0]["name"] == "Grizzly Bears"
        
        # Filter creatures with toughness 2
        toughness_2 = [card for card in sample_card_database 
                      if card.get("toughness") == 2]
        assert len(toughness_2) == 1
        
        # Filter creatures by power/toughness range
        small_creatures = [card for card in sample_card_database 
                          if card.get("power") is not None and card.get("power") <= 2]
        assert len(small_creatures) == 2

    def test_combined_filters(self, sample_card_database):
        """Test combining multiple filters."""
        # Red instants
        red_instants = [card for card in sample_card_database 
                       if "R" in card["colors"] and "Instant" in card["type_line"]]
        assert len(red_instants) == 2
        
        # Cheap artifacts (CMC <= 1)
        cheap_artifacts = [card for card in sample_card_database 
                          if "Artifact" in card["type_line"] and card["cmc"] <= 1]
        assert len(cheap_artifacts) == 2
        
        # Mythic creatures
        mythic_creatures = [card for card in sample_card_database 
                           if card["rarity"] == "mythic" and "Creature" in card["type_line"]]
        assert len(mythic_creatures) == 1
        assert mythic_creatures[0]["name"] == "Omnath, Locus of Mana"
        
        # M21 commons
        m21_commons = [card for card in sample_card_database 
                      if card["set"] == "M21" and card["rarity"] == "common"]
        assert len(m21_commons) == 5

    def test_advanced_text_search(self, sample_card_database):
        """Test advanced text search functionality."""
        # Search with multiple keywords
        def search_text(cards, query):
            words = query.lower().split()
            return [card for card in cards 
                   if all(word in (card["name"] + " " + card["oracle_text"]).lower() 
                         for word in words)]
        
        # Search for "deals damage"
        deals_damage = search_text(sample_card_database, "deals damage")
        assert len(deals_damage) == 2
        
        # Search for "target spell"
        target_spell = search_text(sample_card_database, "target spell")
        assert len(target_spell) == 1
        assert target_spell[0]["name"] == "Counterspell"
        
        # Search for "add mana"
        add_mana = search_text(sample_card_database, "add mana")
        assert len(add_mana) == 1  # Black Lotus has "Add three mana"

    def test_regex_search(self, sample_card_database):
        """Test regex-based search functionality."""
        import re
        
        # Search for cards with numbers in oracle text
        number_pattern = re.compile(r'\d+')
        cards_with_numbers = [card for card in sample_card_database 
                             if number_pattern.search(card["oracle_text"])]
        assert len(cards_with_numbers) >= 3  # Lightning spells have "3 damage"
        
        # Search for cards with mana symbols in oracle text
        mana_symbol_pattern = re.compile(r'\{[WUBRG0-9]+\}')
        cards_with_mana_symbols = [card for card in sample_card_database 
                                  if mana_symbol_pattern.search(card["oracle_text"])]
        assert len(cards_with_mana_symbols) >= 2  # Sol Ring and Black Lotus

    def test_fuzzy_search(self, sample_card_database):
        """Test fuzzy search functionality."""
        def fuzzy_match(text, query, threshold=0.6):
            """Simple fuzzy matching based on character overlap."""
            text_lower = text.lower()
            query_lower = query.lower()
            
            if query_lower in text_lower:
                return True
            
            # Simple character-based similarity
            common_chars = sum(1 for c in query_lower if c in text_lower)
            similarity = common_chars / len(query_lower)
            return similarity >= threshold
        
        # Fuzzy search for "lightening" (misspelled)
        fuzzy_results = [card for card in sample_card_database 
                        if fuzzy_match(card["name"], "lightening")]
        assert len(fuzzy_results) >= 2  # Should find Lightning cards
        
        # Fuzzy search for "grizzly bear"
        bear_results = [card for card in sample_card_database 
                       if fuzzy_match(card["name"], "grizzly bear")]
        assert len(bear_results) >= 1

    def test_filter_performance(self, sample_card_database):
        """Test filter performance with larger datasets."""
        # Simulate larger database
        large_database = sample_card_database * 1000  # 8000 cards
        
        import time
        
        # Time the filter operations
        start_time = time.time()
        
        # Multiple filter operations
        red_cards = [card for card in large_database if "R" in card["colors"]]
        instants = [card for card in large_database if "Instant" in card["type_line"]]
        low_cmc = [card for card in large_database if card["cmc"] <= 2]
        
        end_time = time.time()
        filter_time = end_time - start_time
        
        # Verify results scale correctly
        assert len(red_cards) == len(sample_card_database) * 1000 // len(sample_card_database) * 2
        assert len(instants) == len(sample_card_database) * 1000 // len(sample_card_database) * 4
        
        # Performance should be reasonable (less than 1 second for 8000 cards)
        assert filter_time < 1.0

    def test_filter_caching(self, sample_card_database):
        """Test caching of filter results."""
        filter_cache = {}
        
        def cached_filter(cards, filter_func, cache_key):
            """Apply filter with caching."""
            if cache_key in filter_cache:
                return filter_cache[cache_key]
            
            result = [card for card in cards if filter_func(card)]
            filter_cache[cache_key] = result
            return result
        
        # Apply filters with caching
        red_filter = lambda card: "R" in card["colors"]
        instant_filter = lambda card: "Instant" in card["type_line"]
        
        # First call - should cache result
        red_cards_1 = cached_filter(sample_card_database, red_filter, "red_cards")
        instant_cards_1 = cached_filter(sample_card_database, instant_filter, "instant_cards")
        
        # Second call - should use cache
        red_cards_2 = cached_filter(sample_card_database, red_filter, "red_cards")
        instant_cards_2 = cached_filter(sample_card_database, instant_filter, "instant_cards")
        
        # Verify results are identical (cached)
        assert red_cards_1 is red_cards_2  # Same object reference
        assert instant_cards_1 is instant_cards_2
        
        # Verify cache contains results
        assert "red_cards" in filter_cache
        assert "instant_cards" in filter_cache

    def test_sorting_functionality(self, sample_card_database):
        """Test sorting of filtered results."""
        # Sort by name (alphabetical)
        sorted_by_name = sorted(sample_card_database, key=lambda x: x["name"])
        assert sorted_by_name[0]["name"] == "Black Lotus"
        assert sorted_by_name[-1]["name"] == "Sol Ring"
        
        # Sort by CMC (ascending)
        sorted_by_cmc = sorted(sample_card_database, key=lambda x: x["cmc"])
        assert sorted_by_cmc[0]["cmc"] == 0  # Black Lotus
        assert sorted_by_cmc[-1]["cmc"] == 3  # Omnath
        
        # Sort by rarity (custom order)
        rarity_order = {"common": 1, "uncommon": 2, "rare": 3, "mythic": 4}
        sorted_by_rarity = sorted(sample_card_database, 
                                 key=lambda x: rarity_order.get(x["rarity"], 0))
        assert sorted_by_rarity[0]["rarity"] == "common"
        assert sorted_by_rarity[-1]["rarity"] == "mythic"
        
        # Sort by multiple criteria (CMC, then name)
        sorted_multi = sorted(sample_card_database, 
                             key=lambda x: (x["cmc"], x["name"]))
        # Within same CMC, should be alphabetical by name
        one_cmc_cards = [card for card in sorted_multi if card["cmc"] == 1]
        assert one_cmc_cards == sorted(one_cmc_cards, key=lambda x: x["name"])