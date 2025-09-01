"""Comprehensive deck statistics calculator for Magic: The Gathering decks.

This module provides detailed analysis of MTG decks including mana curve, color distribution,
type breakdown, synergy scoring, and improvement suggestions.
"""

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from statistics import median
from typing import Dict, List, Tuple, Set, Optional
from ...domain.models.mtg_card import MTGCard


# Type alias for card collections
CardCollection = List[MTGCard]


@dataclass
class ManaCurveData:
    """Mana curve statistics for a deck."""
    cmc_distribution: Dict[int, int]
    average_cmc: float
    median_cmc: float


@dataclass
class ColorStats:
    """Color statistics for a deck."""
    color_distribution: Dict[str, int]
    color_requirements: Dict[str, int]  # pip requirements
    devotion: Dict[str, int]


@dataclass
class TypeDistribution:
    """Card type distribution for a deck."""
    creatures: int
    instants: int
    sorceries: int
    enchantments: int
    artifacts: int
    planeswalkers: int
    lands: int


class DeckStatistics:
    """Calculate comprehensive deck statistics and analysis."""
    
    # Color mappings
    COLOR_SYMBOLS = {'W': 'White', 'U': 'Blue', 'B': 'Black', 'R': 'Red', 'G': 'Green'}
    COLOR_ABBREVIATIONS = {'W': 'W', 'U': 'U', 'B': 'B', 'R': 'R', 'G': 'G'}
    
    # Card type keywords for classification
    CREATURE_KEYWORDS = ['creature', 'kreatur']
    INSTANT_KEYWORDS = ['instant', 'spontanzauber']
    SORCERY_KEYWORDS = ['sorcery', 'hexerei']
    ENCHANTMENT_KEYWORDS = ['enchantment', 'verzauberung']
    ARTIFACT_KEYWORDS = ['artifact', 'artefakt']
    PLANESWALKER_KEYWORDS = ['planeswalker', 'planeswalker']
    LAND_KEYWORDS = ['land', 'land']
    
    # Tribal synergies and archetypes
    TRIBAL_TYPES = {
        'angels', 'demons', 'dragons', 'elves', 'goblins', 'humans', 'merfolk',
        'soldiers', 'wizards', 'zombies', 'vampires', 'spirits', 'beasts',
        'elementals', 'knights', 'warriors', 'clerics', 'rogues', 'shamans'
    }
    
    # Removal categories
    REMOVAL_KEYWORDS = {
        'targeted': ['destroy', 'exile', 'damage', 'kill', 'return to hand', 'bounce'],
        'board_wipes': ['destroy all', 'exile all', 'damage to all', 'wrath', 'board wipe'],
        'counters': ['counter', 'counterspell', 'negate']
    }
    
    # Card advantage keywords
    CARD_ADVANTAGE_KEYWORDS = {
        'draw': ['draw', 'card', 'cards'],
        'tutors': ['search', 'tutor', 'library'],
        'recursion': ['return', 'graveyard', 'recursion']
    }
    
    # Win condition keywords
    WIN_CONDITION_KEYWORDS = [
        'wins the game', 'you win', 'target player loses', 'combat damage',
        'commander damage', 'alternate win condition', 'mill', 'poison'
    ]

    @staticmethod
    def calculate_stats(deck: CardCollection) -> Dict:
        """Calculate all comprehensive deck statistics.
        
        Args:
            deck: List of MTGCard objects
            
        Returns:
            Dictionary containing all calculated statistics
        """
        if not deck:
            return DeckStatistics._empty_stats()
            
        stats = {
            'deck_size': len(deck),
            'mana_curve': DeckStatistics.calculate_mana_curve(deck),
            'color_stats': DeckStatistics.calculate_color_stats(deck),
            'type_distribution': DeckStatistics.calculate_type_distribution(deck),
            'land_ratio': DeckStatistics.calculate_land_ratio(deck),
            'ramp_package': DeckStatistics.calculate_ramp_package(deck),
            'removal_suite': DeckStatistics.calculate_removal_suite(deck),
            'card_advantage': DeckStatistics.calculate_card_advantage(deck),
            'win_conditions': DeckStatistics.calculate_win_conditions(deck),
            'synergy_score': DeckStatistics.calculate_synergy_score(deck),
            'power_level': DeckStatistics.estimate_power_level(deck),
            'improvements': []  # Will be populated by suggest_improvements
        }
        
        # Add improvement suggestions
        stats['improvements'] = DeckStatistics.suggest_improvements(stats)
        
        return stats

    @staticmethod
    def calculate_mana_curve(deck: CardCollection) -> ManaCurveData:
        """Calculate mana curve statistics.
        
        Args:
            deck: List of MTGCard objects
            
        Returns:
            ManaCurveData object with curve statistics
        """
        non_land_cards = [card for card in deck if not card.is_land()]
        
        if not non_land_cards:
            return ManaCurveData(
                cmc_distribution={},
                average_cmc=0.0,
                median_cmc=0.0
            )
        
        # Extract CMC values
        cmc_values = []
        cmc_distribution = defaultdict(int)
        
        for card in non_land_cards:
            cmc = DeckStatistics._extract_cmc(card.cost)
            cmc_values.append(cmc)
            cmc_distribution[cmc] += 1
        
        # Calculate statistics
        average_cmc = sum(cmc_values) / len(cmc_values) if cmc_values else 0.0
        median_cmc = median(cmc_values) if cmc_values else 0.0
        
        return ManaCurveData(
            cmc_distribution=dict(cmc_distribution),
            average_cmc=round(average_cmc, 2),
            median_cmc=median_cmc
        )

    @staticmethod
    def calculate_color_stats(deck: CardCollection) -> ColorStats:
        """Calculate color distribution and requirements.
        
        Args:
            deck: List of MTGCard objects
            
        Returns:
            ColorStats object with color analysis
        """
        color_distribution = defaultdict(int)
        color_requirements = defaultdict(int)
        devotion = defaultdict(int)
        
        for card in deck:
            if not card.cost:
                continue
                
            # Count color presence in mana costs
            colors_in_cost = DeckStatistics._extract_colors_from_cost(card.cost)
            
            for color in colors_in_cost:
                color_distribution[color] += 1
            
            # Count pip requirements (devotion)
            pips = DeckStatistics._count_color_pips(card.cost)
            for color, count in pips.items():
                color_requirements[color] += count
                devotion[color] += count
        
        return ColorStats(
            color_distribution=dict(color_distribution),
            color_requirements=dict(color_requirements),
            devotion=dict(devotion)
        )

    @staticmethod
    def calculate_type_distribution(deck: CardCollection) -> TypeDistribution:
        """Calculate card type distribution.
        
        Args:
            deck: List of MTGCard objects
            
        Returns:
            TypeDistribution object with type counts
        """
        counts = {
            'creatures': 0,
            'instants': 0,
            'sorceries': 0,
            'enchantments': 0,
            'artifacts': 0,
            'planeswalkers': 0,
            'lands': 0
        }
        
        for card in deck:
            card_type = card.type.lower()
            
            if any(keyword in card_type for keyword in DeckStatistics.CREATURE_KEYWORDS):
                counts['creatures'] += 1
            elif any(keyword in card_type for keyword in DeckStatistics.INSTANT_KEYWORDS):
                counts['instants'] += 1
            elif any(keyword in card_type for keyword in DeckStatistics.SORCERY_KEYWORDS):
                counts['sorceries'] += 1
            elif any(keyword in card_type for keyword in DeckStatistics.ENCHANTMENT_KEYWORDS):
                counts['enchantments'] += 1
            elif any(keyword in card_type for keyword in DeckStatistics.ARTIFACT_KEYWORDS):
                counts['artifacts'] += 1
            elif any(keyword in card_type for keyword in DeckStatistics.PLANESWALKER_KEYWORDS):
                counts['planeswalkers'] += 1
            elif any(keyword in card_type for keyword in DeckStatistics.LAND_KEYWORDS):
                counts['lands'] += 1
        
        return TypeDistribution(**counts)

    @staticmethod
    def calculate_land_ratio(deck: CardCollection) -> float:
        """Calculate the ratio of lands to total cards.
        
        Args:
            deck: List of MTGCard objects
            
        Returns:
            Land ratio as a percentage
        """
        if not deck:
            return 0.0
            
        land_count = sum(1 for card in deck if card.is_land())
        return round((land_count / len(deck)) * 100, 1)

    @staticmethod
    def calculate_ramp_package(deck: CardCollection) -> Dict:
        """Calculate mana acceleration package analysis.
        
        Args:
            deck: List of MTGCard objects
            
        Returns:
            Dictionary with ramp analysis
        """
        ramp_data = {
            'mana_rocks': 0,
            'mana_dorks': 0,
            'ramp_spells': 0,
            'total_ramp': 0,
            'ramp_cards': []
        }
        
        ramp_keywords = [
            'mana', 'add', 'lands', 'basic land', 'ramp', 'sol ring',
            'signet', 'talisman', 'myr', 'elf', 'birds of paradise'
        ]
        
        for card in deck:
            card_text = (card.text or '').lower()
            card_type = card.type.lower()
            card_name = card.name.lower()
            
            is_ramp = False
            ramp_type = None
            
            # Check for mana rocks (artifacts that add mana)
            if 'artifact' in card_type and any(keyword in card_text for keyword in ['add', 'mana']):
                ramp_data['mana_rocks'] += 1
                ramp_type = 'mana_rock'
                is_ramp = True
            
            # Check for mana dorks (creatures that add mana)
            elif 'creature' in card_type and any(keyword in card_text for keyword in ['add', 'mana']):
                ramp_data['mana_dorks'] += 1
                ramp_type = 'mana_dork'
                is_ramp = True
            
            # Check for ramp spells
            elif any(keyword in card_text for keyword in ['search', 'basic land', 'ramp']):
                ramp_data['ramp_spells'] += 1
                ramp_type = 'ramp_spell'
                is_ramp = True
            
            if is_ramp:
                ramp_data['ramp_cards'].append({
                    'name': card.name,
                    'type': ramp_type,
                    'cmc': DeckStatistics._extract_cmc(card.cost)
                })
        
        ramp_data['total_ramp'] = ramp_data['mana_rocks'] + ramp_data['mana_dorks'] + ramp_data['ramp_spells']
        
        return ramp_data

    @staticmethod
    def calculate_removal_suite(deck: CardCollection) -> Dict:
        """Calculate removal package analysis.
        
        Args:
            deck: List of MTGCard objects
            
        Returns:
            Dictionary with removal analysis
        """
        removal_data = {
            'targeted_removal': 0,
            'board_wipes': 0,
            'counterspells': 0,
            'total_removal': 0,
            'removal_cards': []
        }
        
        for card in deck:
            card_text = (card.text or '').lower()
            card_name = card.name.lower()
            
            removal_type = None
            is_removal = False
            
            # Check for board wipes
            if any(keyword in card_text for keyword in DeckStatistics.REMOVAL_KEYWORDS['board_wipes']):
                removal_data['board_wipes'] += 1
                removal_type = 'board_wipe'
                is_removal = True
            
            # Check for counterspells
            elif any(keyword in card_text for keyword in DeckStatistics.REMOVAL_KEYWORDS['counters']):
                removal_data['counterspells'] += 1
                removal_type = 'counterspell'
                is_removal = True
            
            # Check for targeted removal
            elif any(keyword in card_text for keyword in DeckStatistics.REMOVAL_KEYWORDS['targeted']):
                removal_data['targeted_removal'] += 1
                removal_type = 'targeted_removal'
                is_removal = True
            
            if is_removal:
                removal_data['removal_cards'].append({
                    'name': card.name,
                    'type': removal_type,
                    'cmc': DeckStatistics._extract_cmc(card.cost)
                })
        
        removal_data['total_removal'] = (
            removal_data['targeted_removal'] + 
            removal_data['board_wipes'] + 
            removal_data['counterspells']
        )
        
        return removal_data

    @staticmethod
    def calculate_card_advantage(deck: CardCollection) -> Dict:
        """Calculate card advantage analysis.
        
        Args:
            deck: List of MTGCard objects
            
        Returns:
            Dictionary with card advantage analysis
        """
        card_advantage_data = {
            'card_draw': 0,
            'tutors': 0,
            'recursion': 0,
            'total_card_advantage': 0,
            'card_advantage_cards': []
        }
        
        for card in deck:
            card_text = (card.text or '').lower()
            card_name = card.name.lower()
            
            advantage_type = None
            is_advantage = False
            
            # Check for tutors
            if any(keyword in card_text for keyword in DeckStatistics.CARD_ADVANTAGE_KEYWORDS['tutors']):
                card_advantage_data['tutors'] += 1
                advantage_type = 'tutor'
                is_advantage = True
            
            # Check for recursion
            elif any(keyword in card_text for keyword in DeckStatistics.CARD_ADVANTAGE_KEYWORDS['recursion']):
                card_advantage_data['recursion'] += 1
                advantage_type = 'recursion'
                is_advantage = True
            
            # Check for card draw
            elif any(keyword in card_text for keyword in DeckStatistics.CARD_ADVANTAGE_KEYWORDS['draw']):
                card_advantage_data['card_draw'] += 1
                advantage_type = 'card_draw'
                is_advantage = True
            
            if is_advantage:
                card_advantage_data['card_advantage_cards'].append({
                    'name': card.name,
                    'type': advantage_type,
                    'cmc': DeckStatistics._extract_cmc(card.cost)
                })
        
        card_advantage_data['total_card_advantage'] = (
            card_advantage_data['card_draw'] + 
            card_advantage_data['tutors'] + 
            card_advantage_data['recursion']
        )
        
        return card_advantage_data

    @staticmethod
    def calculate_win_conditions(deck: CardCollection) -> List[str]:
        """Identify potential win conditions in the deck.
        
        Args:
            deck: List of MTGCard objects
            
        Returns:
            List of identified win conditions
        """
        win_conditions = []
        
        # Track potential win cons
        combat_creatures = 0
        alternate_wins = []
        
        for card in deck:
            card_text = (card.text or '').lower()
            card_name = card.name.lower()
            
            # Check for explicit win conditions
            for win_keyword in DeckStatistics.WIN_CONDITION_KEYWORDS:
                if win_keyword in card_text:
                    alternate_wins.append(f"{card.name} ({win_keyword})")
                    break
            
            # Count potential combat win conditions
            if card.is_creature() and card.power and card.power >= 3:
                combat_creatures += 1
        
        # Determine win conditions
        if combat_creatures >= 10:
            win_conditions.append("Combat damage (creature beatdown)")
        elif combat_creatures >= 5:
            win_conditions.append("Combat damage (moderate creature pressure)")
        
        if alternate_wins:
            win_conditions.extend(alternate_wins)
        
        if not win_conditions:
            win_conditions.append("Win condition unclear - may need more focus")
        
        return win_conditions

    @staticmethod
    def calculate_synergy_score(deck: CardCollection) -> float:
        """Calculate deck synergy score (0-100).
        
        Args:
            deck: List of MTGCard objects
            
        Returns:
            Synergy score from 0-100
        """
        if not deck:
            return 0.0
        
        scores = []
        
        # 1. Tribal synergy (0-25 points)
        tribal_score = DeckStatistics._calculate_tribal_synergy(deck)
        scores.append(tribal_score)
        
        # 2. Color consistency (0-25 points)  
        color_consistency = DeckStatistics._calculate_color_consistency(deck)
        scores.append(color_consistency)
        
        # 3. Mana curve efficiency (0-25 points)
        curve_efficiency = DeckStatistics._calculate_curve_efficiency(deck)
        scores.append(curve_efficiency)
        
        # 4. Card type balance (0-25 points)
        type_balance = DeckStatistics._calculate_type_balance(deck)
        scores.append(type_balance)
        
        return round(sum(scores), 1)

    @staticmethod
    def estimate_power_level(deck: CardCollection) -> int:
        """Estimate deck power level on a 1-10 scale.
        
        Args:
            deck: List of MTGCard objects
            
        Returns:
            Power level from 1-10
        """
        if not deck:
            return 1
        
        power_indicators = 0
        
        # High-power indicators
        expensive_spells = sum(1 for card in deck if not card.is_land() and DeckStatistics._extract_cmc(card.cost) >= 7)
        cheap_efficient_spells = sum(1 for card in deck if not card.is_land() and DeckStatistics._extract_cmc(card.cost) <= 2)
        
        # Ramp and card advantage
        ramp_package = DeckStatistics.calculate_ramp_package(deck)
        card_advantage = DeckStatistics.calculate_card_advantage(deck)
        ramp_count = ramp_package['total_ramp']
        card_advantage_count = card_advantage['total_card_advantage']
        
        # Calculate power level
        base_power = 3  # Default casual level
        
        # Efficient low-cost spells indicate higher power
        if cheap_efficient_spells >= 15:
            power_indicators += 2
        elif cheap_efficient_spells >= 10:
            power_indicators += 1
        
        # Good ramp package
        if ramp_count >= 12:
            power_indicators += 2
        elif ramp_count >= 8:
            power_indicators += 1
        
        # Card advantage engines
        if card_advantage_count >= 10:
            power_indicators += 2
        elif card_advantage_count >= 6:
            power_indicators += 1
        
        # Expensive haymaker spells (can indicate both high and low power)
        if expensive_spells >= 8:
            power_indicators -= 1  # Too many expensive spells = less competitive
        
        final_power = max(1, min(10, base_power + power_indicators))
        return final_power

    @staticmethod
    def suggest_improvements(stats: Dict) -> List[str]:
        """Generate actionable improvement suggestions based on statistics.
        
        Args:
            stats: Dictionary of calculated statistics
            
        Returns:
            List of improvement suggestions
        """
        suggestions = []
        
        # Land ratio suggestions
        land_ratio = stats['land_ratio']
        if land_ratio < 35:
            suggestions.append(f"Consider adding more lands (currently {land_ratio}%, recommend 35-40%)")
        elif land_ratio > 45:
            suggestions.append(f"Consider reducing lands (currently {land_ratio}%, may be too many)")
        
        # Mana curve suggestions
        mana_curve = stats['mana_curve']
        avg_cmc = mana_curve.average_cmc
        if avg_cmc > 4.0:
            suggestions.append(f"Mana curve is high (avg {avg_cmc}), consider adding cheaper spells")
        elif avg_cmc < 2.0:
            suggestions.append(f"Mana curve is very low (avg {avg_cmc}), may lack impact")
        
        # Ramp suggestions
        ramp_package = stats['ramp_package']
        if ramp_package['total_ramp'] < 6:
            suggestions.append("Consider adding more mana ramp (currently under 6 sources)")
        
        # Removal suggestions
        removal_suite = stats['removal_suite']
        if removal_suite['total_removal'] < 8:
            suggestions.append("Consider adding more removal spells (currently under 8)")
        
        # Card advantage suggestions
        card_advantage = stats['card_advantage']
        if card_advantage['total_card_advantage'] < 6:
            suggestions.append("Consider adding more card draw/advantage engines")
        
        # Color distribution suggestions
        color_stats = stats['color_stats']
        num_colors = len(color_stats.color_distribution)
        if num_colors >= 4:
            suggestions.append("Multi-color deck may need better mana fixing")
        
        # Win condition suggestions
        win_conditions = stats['win_conditions']
        if len(win_conditions) == 1 and "unclear" in win_conditions[0]:
            suggestions.append("Deck lacks clear win conditions - consider adding finishers")
        
        # Synergy score suggestions
        synergy_score = stats['synergy_score']
        if synergy_score < 50:
            suggestions.append(f"Synergy score is low ({synergy_score}/100) - focus on tribal or thematic coherence")
        
        if not suggestions:
            suggestions.append("Deck looks well-balanced! Consider fine-tuning based on meta and playtesting")
        
        return suggestions

    @staticmethod
    def export_to_dict(stats: Dict) -> Dict:
        """Export statistics to dictionary format.
        
        Args:
            stats: Statistics dictionary
            
        Returns:
            Dictionary with all statistics
        """
        return stats

    @staticmethod
    def export_to_json(stats: Dict) -> str:
        """Export statistics to JSON format.
        
        Args:
            stats: Statistics dictionary
            
        Returns:
            JSON string representation
        """
        # Convert dataclasses to dicts for JSON serialization
        json_stats = DeckStatistics._prepare_for_json(stats)
        return json.dumps(json_stats, indent=2)

    @staticmethod
    def export_to_markdown_report(stats: Dict) -> str:
        """Export statistics to formatted markdown report.
        
        Args:
            stats: Statistics dictionary
            
        Returns:
            Markdown formatted report
        """
        report = []
        
        # Header
        report.append("# MTG Deck Analysis Report")
        report.append("")
        
        # Deck Overview
        report.append("## Deck Overview")
        report.append(f"**Total Cards:** {stats['deck_size']}")
        report.append(f"**Land Ratio:** {stats['land_ratio']}%")
        report.append(f"**Synergy Score:** {stats['synergy_score']}/100")
        report.append(f"**Estimated Power Level:** {stats['power_level']}/10")
        report.append("")
        
        # Mana Curve
        mana_curve = stats['mana_curve']
        report.append("## Mana Curve")
        report.append(f"**Average CMC:** {mana_curve.average_cmc}")
        report.append(f"**Median CMC:** {mana_curve.median_cmc}")
        report.append("**CMC Distribution:**")
        for cmc, count in sorted(mana_curve.cmc_distribution.items()):
            report.append(f"- {cmc} CMC: {count} cards")
        report.append("")
        
        # Color Analysis
        color_stats = stats['color_stats']
        report.append("## Color Analysis")
        if color_stats.color_distribution:
            report.append("**Color Distribution:**")
            for color, count in color_stats.color_distribution.items():
                report.append(f"- {color}: {count} cards")
            
            report.append("**Pip Requirements:**")
            for color, pips in color_stats.color_requirements.items():
                report.append(f"- {color}: {pips} pips")
        else:
            report.append("*No colored mana requirements found*")
        report.append("")
        
        # Type Distribution
        type_dist = stats['type_distribution']
        report.append("## Card Types")
        report.append(f"**Creatures:** {type_dist.creatures}")
        report.append(f"**Instants:** {type_dist.instants}")
        report.append(f"**Sorceries:** {type_dist.sorceries}")
        report.append(f"**Enchantments:** {type_dist.enchantments}")
        report.append(f"**Artifacts:** {type_dist.artifacts}")
        report.append(f"**Planeswalkers:** {type_dist.planeswalkers}")
        report.append(f"**Lands:** {type_dist.lands}")
        report.append("")
        
        # Deck Components
        report.append("## Deck Components")
        
        ramp = stats['ramp_package']
        report.append(f"**Ramp Package:** {ramp['total_ramp']} cards")
        report.append(f"- Mana Rocks: {ramp['mana_rocks']}")
        report.append(f"- Mana Dorks: {ramp['mana_dorks']}")
        report.append(f"- Ramp Spells: {ramp['ramp_spells']}")
        report.append("")
        
        removal = stats['removal_suite']
        report.append(f"**Removal Suite:** {removal['total_removal']} cards")
        report.append(f"- Targeted Removal: {removal['targeted_removal']}")
        report.append(f"- Board Wipes: {removal['board_wipes']}")
        report.append(f"- Counterspells: {removal['counterspells']}")
        report.append("")
        
        card_adv = stats['card_advantage']
        report.append(f"**Card Advantage:** {card_adv['total_card_advantage']} cards")
        report.append(f"- Card Draw: {card_adv['card_draw']}")
        report.append(f"- Tutors: {card_adv['tutors']}")
        report.append(f"- Recursion: {card_adv['recursion']}")
        report.append("")
        
        # Win Conditions
        report.append("## Win Conditions")
        for win_con in stats['win_conditions']:
            report.append(f"- {win_con}")
        report.append("")
        
        # Improvement Suggestions
        if stats['improvements']:
            report.append("## Suggested Improvements")
            for suggestion in stats['improvements']:
                report.append(f"- {suggestion}")
        report.append("")
        
        return "\n".join(report)

    # Helper Methods

    @staticmethod
    def _extract_cmc(mana_cost: str) -> int:
        """Extract converted mana cost from mana cost string.
        
        Args:
            mana_cost: Mana cost string (e.g., "{2}{U}{R}" or "2UR")
            
        Returns:
            Converted mana cost as integer
        """
        if not mana_cost or mana_cost == "-":
            return 0
        
        # Remove braces if present
        clean_cost = mana_cost.replace("{", "").replace("}", "")
        
        total_cmc = 0
        i = 0
        
        while i < len(clean_cost):
            char = clean_cost[i]
            
            # Handle multi-digit numbers
            if char.isdigit():
                j = i
                while j < len(clean_cost) and clean_cost[j].isdigit():
                    j += 1
                total_cmc += int(clean_cost[i:j])
                i = j
            # Handle color symbols and X
            elif char.upper() in 'WUBRGX':
                total_cmc += 1
                i += 1
            else:
                i += 1
        
        return total_cmc

    @staticmethod
    def _extract_colors_from_cost(mana_cost: str) -> Set[str]:
        """Extract color symbols from mana cost.
        
        Args:
            mana_cost: Mana cost string
            
        Returns:
            Set of color symbols present
        """
        if not mana_cost:
            return set()
        
        colors = set()
        color_symbols = set('WUBRG')
        
        for char in mana_cost.upper():
            if char in color_symbols:
                colors.add(char)
        
        return colors

    @staticmethod
    def _count_color_pips(mana_cost: str) -> Dict[str, int]:
        """Count color pip requirements in mana cost.
        
        Args:
            mana_cost: Mana cost string
            
        Returns:
            Dictionary of color pip counts
        """
        if not mana_cost:
            return {}
        
        pip_count = Counter()
        color_symbols = set('WUBRG')
        
        for char in mana_cost.upper():
            if char in color_symbols:
                pip_count[char] += 1
        
        return dict(pip_count)

    @staticmethod
    def _calculate_tribal_synergy(deck: CardCollection) -> float:
        """Calculate tribal synergy score (0-25).
        
        Args:
            deck: List of MTGCard objects
            
        Returns:
            Tribal synergy score
        """
        creature_types = Counter()
        
        for card in deck:
            if card.is_creature():
                card_type = card.type.lower()
                # Extract creature types (simplified)
                for tribal_type in DeckStatistics.TRIBAL_TYPES:
                    if tribal_type in card_type:
                        creature_types[tribal_type] += 1
        
        if not creature_types:
            return 0.0
        
        # Award points for tribal concentration
        max_tribal = max(creature_types.values())
        total_creatures = sum(1 for card in deck if card.is_creature())
        
        if total_creatures == 0:
            return 0.0
        
        tribal_percentage = max_tribal / total_creatures
        
        if tribal_percentage >= 0.6:
            return 25.0
        elif tribal_percentage >= 0.4:
            return 20.0
        elif tribal_percentage >= 0.3:
            return 15.0
        elif tribal_percentage >= 0.2:
            return 10.0
        else:
            return 5.0

    @staticmethod
    def _calculate_color_consistency(deck: CardCollection) -> float:
        """Calculate color consistency score (0-25).
        
        Args:
            deck: List of MTGCard objects
            
        Returns:
            Color consistency score
        """
        color_stats = DeckStatistics.calculate_color_stats(deck)
        colors = len(color_stats.color_distribution)
        
        # Award points based on color focus
        if colors == 0:
            return 25.0  # Colorless
        elif colors == 1:
            return 25.0  # Mono-color
        elif colors == 2:
            return 20.0  # Two-color
        elif colors == 3:
            return 15.0  # Three-color
        elif colors == 4:
            return 10.0  # Four-color
        else:
            return 5.0   # Five-color

    @staticmethod
    def _calculate_curve_efficiency(deck: CardCollection) -> float:
        """Calculate mana curve efficiency score (0-25).
        
        Args:
            deck: List of MTGCard objects
            
        Returns:
            Curve efficiency score
        """
        mana_curve = DeckStatistics.calculate_mana_curve(deck)
        
        # Ideal curve has reasonable distribution across CMC 1-4
        avg_cmc = mana_curve.average_cmc
        
        if 2.5 <= avg_cmc <= 3.5:
            return 25.0
        elif 2.0 <= avg_cmc <= 4.0:
            return 20.0
        elif 1.5 <= avg_cmc <= 4.5:
            return 15.0
        elif 1.0 <= avg_cmc <= 5.0:
            return 10.0
        else:
            return 5.0

    @staticmethod
    def _calculate_type_balance(deck: CardCollection) -> float:
        """Calculate card type balance score (0-25).
        
        Args:
            deck: List of MTGCard objects
            
        Returns:
            Type balance score
        """
        type_dist = DeckStatistics.calculate_type_distribution(deck)
        non_land_total = (
            type_dist.creatures + type_dist.instants + type_dist.sorceries +
            type_dist.enchantments + type_dist.artifacts + type_dist.planeswalkers
        )
        
        if non_land_total == 0:
            return 0.0
        
        # Award points for having a mix of card types
        type_counts = [
            type_dist.creatures, type_dist.instants, type_dist.sorceries,
            type_dist.enchantments, type_dist.artifacts, type_dist.planeswalkers
        ]
        
        non_zero_types = sum(1 for count in type_counts if count > 0)
        
        if non_zero_types >= 4:
            return 25.0
        elif non_zero_types >= 3:
            return 20.0
        elif non_zero_types >= 2:
            return 15.0
        else:
            return 10.0

    @staticmethod
    def _prepare_for_json(stats: Dict) -> Dict:
        """Prepare statistics dictionary for JSON serialization.
        
        Args:
            stats: Statistics dictionary
            
        Returns:
            JSON-serializable dictionary
        """
        json_stats = {}
        
        for key, value in stats.items():
            if hasattr(value, '__dict__'):  # dataclass
                json_stats[key] = value.__dict__
            else:
                json_stats[key] = value
        
        return json_stats

    @staticmethod
    def _empty_stats() -> Dict:
        """Return empty statistics dictionary.
        
        Returns:
            Empty statistics dictionary
        """
        return {
            'deck_size': 0,
            'mana_curve': ManaCurveData({}, 0.0, 0.0),
            'color_stats': ColorStats({}, {}, {}),
            'type_distribution': TypeDistribution(0, 0, 0, 0, 0, 0, 0),
            'land_ratio': 0.0,
            'ramp_package': {'mana_rocks': 0, 'mana_dorks': 0, 'ramp_spells': 0, 'total_ramp': 0, 'ramp_cards': []},
            'removal_suite': {'targeted_removal': 0, 'board_wipes': 0, 'counterspells': 0, 'total_removal': 0, 'removal_cards': []},
            'card_advantage': {'card_draw': 0, 'tutors': 0, 'recursion': 0, 'total_card_advantage': 0, 'card_advantage_cards': []},
            'win_conditions': ['No cards to analyze'],
            'synergy_score': 0.0,
            'power_level': 1,
            'improvements': ['Add cards to analyze deck']
        }