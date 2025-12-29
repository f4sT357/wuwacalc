from utils.constants import (
    STAT_CRIT_RATE, STAT_CRIT_DMG, STAT_ATK_PERCENT, STAT_ATK_FLAT, STAT_ER,
    CV_KEY_CRIT_RATE, CV_KEY_CRIT_DMG, CV_KEY_ATK_PERCENT, 
    CV_KEY_ATK_FLAT_DIVISOR, CV_KEY_ATK_FLAT_MULTIPLIER, CV_KEY_ER, CV_KEY_DMG_BONUS,
    DAMAGE_BONUS_STATS
)
from core.data_contracts import EvaluationResult

class EchoData:
    """Echo data class (extended version)."""
    def __init__(self, cost: int, main_stat: str, substats: dict[str, float]):
        self.cost = cost
        self.main_stat = main_stat
        self.substats = substats
        self.level = 25
        self.score = 0.0
        self.rating = ""
        self.effective_stats_count = 0

    def calculate_score(self, stat_weights: dict[str, float], substat_max_values: dict[str, float], main_stat_multiplier: float) -> float:
        """Standard score calculation (normalization method).

        Args:
            stat_weights: Dictionary of weights.
            substat_max_values: Dictionary of max values for substats.
            main_stat_multiplier: Multiplier for the main stat.
        Returns:
            The calculated score.
        """
        if stat_weights is None:
            # Prevent crash if weights missing, though caller should provide
            return 0.0 
        
        main_score = main_stat_multiplier
        sub_score = 0.0
        
        for stat_name, stat_value in self.substats.items():
            if stat_name in substat_max_values and stat_name in stat_weights:
                max_value = substat_max_values[stat_name]
                weight = stat_weights[stat_name]
                normalized = (stat_value / max_value / 5)
                sub_score += weight * normalized * 100
        
        self.score = (self.level / 25) * (main_score + sub_score)
        return self.score

    def calculate_score_normalized(self, stat_weights, substat_max_values, main_stat_multiplier):
        """Method 1: Normalized Score (GameWith style) - 0-100 points"""
        main_score = main_stat_multiplier
        sub_score = 0.0
        
        for stat_name, stat_value in self.substats.items():
            max_val = substat_max_values.get(stat_name, 1)
            weight = stat_weights.get(stat_name, 0)
            normalized = (stat_value / max_val / 5) * weight * 100
            sub_score += normalized
        
        total = (self.level / 25) * (main_score + sub_score)
        return total

    def calculate_score_ratio_based(self, importance_weights, substat_max_values):
        """Method 2: Ratio-Based Method (Keisan style)"""
        score = 0.0
        
        for stat_name, stat_value in self.substats.items():
            max_val = substat_max_values.get(stat_name, 1)
            importance = importance_weights.get(stat_name, 0)
            ratio = (stat_value / max_val / 5) * importance
            score += ratio
        
        final_score = (100 * self.level / 25) * score
        return final_score

    def calculate_score_roll_quality(self, stat_weights, roll_quality_config):
        """Method 3: Roll Quality Method"""
        if not roll_quality_config:
            return 0.0
            
        ranges_config = roll_quality_config.get("ranges", {})
        points_config = roll_quality_config.get("points", {})
        
        quality_points = 0
        count = 0
        
        for stat_name, stat_value in self.substats.items():
            if stat_name not in ranges_config:
                continue
                
            ranges = ranges_config[stat_name]
            weight = stat_weights.get(stat_name, 0.5)
            
            if stat_value >= ranges.get("Max", 999):
                quality_points += points_config.get("Max", 3) * weight
            elif stat_value >= ranges.get("Good", 999):
                quality_points += points_config.get("Good", 2) * weight
            elif stat_value >= ranges.get("Low", 999):
                quality_points += points_config.get("Low", 1) * weight
            else:
                quality_points += points_config.get("Default", 0.5) * weight
            count += 1
        
        score = (quality_points / (count * 3)) * 100 if count > 0 else 0
        return score * (self.level / 25)


    def calculate_score_effective_stats(self, stat_weights, substat_max_values, effective_stats_config):
        """Method 4: Effective Stats Count Method"""
        effective_count = 0
        total_contribution = 0
        
        threshold = effective_stats_config.get("threshold", 0.5)
        eps = 1e-9
        
        # Substats only (Main stat is excluded as per user confirmation)
        base_multiplier = effective_stats_config.get("base_multiplier", 20)
        bonus_multipliers = effective_stats_config.get("bonus_multiplier", {})
        
        effective_details = []
        for stat_name, stat_value in self.substats.items():
            weight = stat_weights.get(stat_name, 0)
            
            is_effective = weight >= (threshold - eps)
            if is_effective:
                effective_count += 1
                max_val = substat_max_values.get(stat_name, 1)
                contribution = (stat_value / max_val) * weight * base_multiplier
                total_contribution += contribution
                effective_details.append(f"{stat_name}({weight})")
            else:
                effective_details.append(f"[{stat_name}({weight})]")
        
        # Log the breakdown of effective stats (names in [] are non-effective)
        # This will help identify if a stat was misidentified or has 0 weight
        # print(f"Effective stats detail: {', '.join(effective_details)}")
        
        bonus = bonus_multipliers.get(str(effective_count), bonus_multipliers.get("default", 0.5))
        
        score = total_contribution * bonus * (self.level / 25)
        self.effective_stats_count = effective_count
        return score

    def calculate_score_cv_based(self, stat_weights, cv_weights, stat_offsets=None):
        """Method 5: CV (Crit Value) Based Method - Community Standard"""
        if stat_offsets is None: stat_offsets = {}
        cv_score = 0.0
        
        # Basic CV calculation (most important)
        crit_rate = self.substats.get(STAT_CRIT_RATE, 0)
        crit_dmg = self.substats.get(STAT_CRIT_DMG, 0)
        
        # Apply offset (e.g. from weapon or base stats)
        total_crit_rate = crit_rate + stat_offsets.get(STAT_CRIT_RATE, 0.0)
        
        cv_score += (crit_rate * cv_weights.get(CV_KEY_CRIT_RATE, 2.0)) + \
                    (crit_dmg * cv_weights.get(CV_KEY_CRIT_DMG, 1.0))
        
        # Extended scoring with other valuable stats
        # We use the raw substat values for the "Echo Score", 
        # but the offsets could be used to weight their importance if we wanted to.
        atk_pct = self.substats.get(STAT_ATK_PERCENT, 0)
        flat_atk = self.substats.get(STAT_ATK_FLAT, 0)
        er = self.substats.get(STAT_ER, 0)
        
        cv_score += (atk_pct * cv_weights.get(CV_KEY_ATK_PERCENT, 1.1))
        cv_score += (flat_atk / cv_weights.get(CV_KEY_ATK_FLAT_DIVISOR, 10.0) * cv_weights.get(CV_KEY_ATK_FLAT_MULTIPLIER, 1.2))
        cv_score += (er * cv_weights.get(CV_KEY_ER, 0.5))
        
        # Character-specific damage bonuses (weighted by character preference)
        dmg_bonus_weight = cv_weights.get(CV_KEY_DMG_BONUS, 1.1)

        for stat_name in DAMAGE_BONUS_STATS:
            if stat_name in self.substats:
                stat_value = self.substats[stat_name]
                weight = stat_weights.get(stat_name, 0.5)
                # Damage bonuses are weighted by character preference and multiplied by weight
                cv_score += (stat_value * dmg_bonus_weight * weight)
        
        # Level scaling
        final_score = cv_score * (self.level / 25)
        return final_score

    def calculate_theoretical_max_sub_score(self, stat_weights, substat_max_values):
        """
        Calculates the theoretical maximum score for 5 substat slots
        based on the highest weighted stats for this character.
        """
        if not stat_weights:
            return 100.0 # Fallback
            
        # Get all stats that have a weight, sorted by weight descending
        weighted_stats = sorted(
            [(name, weight) for name, weight in stat_weights.items() if weight > 0],
            key=lambda x: x[1], reverse=True
        )
        
        # Take the top 5 weighted stats
        top_5 = weighted_stats[:5]
        
        max_sub_score = 0.0
        for name, weight in top_5:
            max_val = substat_max_values.get(name, 1.0)
            # 1 slot maximum normalized score: (max_val / max_val / 5) * weight * 100 = 20 * weight
            max_sub_score += 20.0 * weight
            
        return max_sub_score if max_sub_score > 0 else 100.0

    def evaluate_comprehensive(self, character_weights, config_bundle, enabled_methods=None, 
                               stat_offsets=None, base_stats=None, ideal_stats=None, scaling_stat="攻撃力"):
        """Comprehensive evaluation using provided configuration.
        
        Args:
            character_weights: Dictionary of stat weights for the character
            config_bundle: Dictionary containing all configuration data (max_values, multipliers, etc.)
            enabled_methods: Dictionary of {method_name: bool} indicating which methods to use.
            stat_offsets: Dictionary of offsets for base/weapon stats.
            base_stats: Dictionary of base values (Char + Weapon).
            ideal_stats: Dictionary of target values.
            scaling_stat: Name of the primary stat for calculation (ATK, DEF, HP).
        """
        if stat_offsets is None: stat_offsets = config_bundle.get("stat_offsets", {})
        if base_stats is None: base_stats = config_bundle.get("base_stats", {})
        if ideal_stats is None: ideal_stats = config_bundle.get("ideal_stats", {})
        
        # Default to all methods enabled if not specified
        if enabled_methods is None:
            enabled_methods = {
                "normalized": True,
                "ratio": True,
                "roll": True,
                "effective": True,
                "cv": True
            }
        
        substat_max_values = config_bundle.get("substat_max_values", {})
        main_stat_multiplier = config_bundle.get("main_stat_multiplier", 15.0)
        
        # Calculate scores for enabled methods only
        results = {}
        if enabled_methods.get("normalized", False):
            results["normalized"] = self.calculate_score_normalized(
                character_weights, substat_max_values, main_stat_multiplier
            )
        if enabled_methods.get("ratio", False):
            results["ratio"] = self.calculate_score_ratio_based(
                character_weights, substat_max_values
            )
        if enabled_methods.get("roll", False):
            results["roll"] = self.calculate_score_roll_quality(
                character_weights, config_bundle.get("roll_quality", {})
            )
        if enabled_methods.get("effective", False):
            results["effective"] = self.calculate_score_effective_stats(
                character_weights, substat_max_values, config_bundle.get("effective_stats", {})
            )
        if enabled_methods.get("cv", False):
            # Pass CRIT offset specifically if present in stat_offsets
            results["cv"] = self.calculate_score_cv_based(
                character_weights, config_bundle.get("cv_weights", {}), stat_offsets=stat_offsets
            )
        
        # New Achievement Rate calculation
        theoretical_max = self.calculate_theoretical_max_sub_score(character_weights, substat_max_values)
        
        current_sub_score = 0.0
        for stat_name, stat_value in self.substats.items():
            max_val = substat_max_values.get(stat_name, 1)
            weight = character_weights.get(stat_name, 0)
            current_sub_score += (stat_value / max_val / 5) * weight * 100
            
        achievement_rate = (current_sub_score / theoretical_max) * 100 if theoretical_max > 0 else 0
        results["achievement"] = achievement_rate

        if results:
            avg_score = sum(v for k, v in results.items() if k != "achievement") / (len(results) - 1 if len(results) > 1 else 1)
        else:
            avg_score = 0.0
        
        rating_key = self.get_rating_by_achievement(achievement_rate, self.cost)

        # Calculate estimated total stats and achievement towards IDEAL
        estimated_stats = {}
        all_stat_names = set(self.substats.keys()) | set(stat_offsets.keys())
        for sname in all_stat_names:
            estimated_stats[sname] = self.substats.get(sname, 0.0) + stat_offsets.get(sname, 0.0)

        # Special logic for Final Stat Calculation (e.g. Total ATK)
        # Final = (Base * (1 + PercentSum/100)) + FlatSum
        from utils.constants import STAT_ATK_PERCENT, STAT_ATK_FLAT, STAT_DEF_PERCENT, STAT_DEF_FLAT, STAT_HP_PERCENT, STAT_HP_FLAT
        
        # Map scaling stat to its percent counterpart
        percent_map = {
            STAT_ATK_FLAT: STAT_ATK_PERCENT,
            STAT_DEF_FLAT: STAT_DEF_PERCENT,
            STAT_HP_FLAT: STAT_HP_PERCENT
        }
        
        final_stat_val = 0.0
        target_stat_val = ideal_stats.get(scaling_stat, 0.0)
        
        if scaling_stat in base_stats:
            base_val = base_stats[scaling_stat]
            p_stat = percent_map.get(scaling_stat)
            
            # Sum up percentages (Echo substat + Offset)
            p_sum = estimated_stats.get(p_stat, 0.0)
            
            # Add Main Stat if it matches the primary stat
            if self.main_stat == p_stat:
                # Main stat value is not directly in substats, need to get it.
                # Usually Main Stat for Cost 4/3/1 is fixed at max level.
                # For now, we use a heuristic or let user include it in offsets.
                pass 
            
            f_sum = estimated_stats.get(scaling_stat, 0.0)
            
            final_stat_val = (base_val * (1 + p_sum / 100)) + f_sum
            estimated_stats[f"Total {scaling_stat}"] = final_stat_val
            
            if target_stat_val > 0:
                estimated_stats[f"Goal {scaling_stat} %"] = (final_stat_val / target_stat_val) * 100

        # Main Stat Consistency Check
        consistency_msg = ""
        is_best = True
        penalty = 1.0
        
        expected_main_stats = config_bundle.get("character_main_stats", {})
        # Find all valid candidates for this cost (e.g., '3', '3_1', '3_2')
        cost_prefix = str(self.cost).split('_')[0]
        possible_targets = [v for k, v in expected_main_stats.items() if k.startswith(cost_prefix)]
        
        if possible_targets:
            # Check for direct match
            if self.main_stat in possible_targets:
                is_best = True
            # Special handling for Element DMG placeholder
            elif "属性ダメージアップ" in possible_targets and "ダメージアップ" in self.main_stat and self.main_stat != "通常攻撃ダメージアップ":
                is_best = True
            # Handle "Acceptable" cases like ATK% for Cost 3 attackers
            elif cost_prefix == "3" and self.main_stat == "攻撃力%" and any("ダメージアップ" in t or t == "属性ダメージアップ" for t in possible_targets):
                is_best = True
                consistency_msg = "攻撃力%は属性ダメージに次ぐ有力な選択肢です（許容範囲）"
                penalty = 0.97 # Slight penalty for not being "optimal"
            else:
                is_best = False
                target_str = " / ".join(set(possible_targets))
                consistency_msg = f"メインステータスが一致しません（理想：{target_str}）"
                penalty = 0.8

        achievement_rate *= penalty

        # Build Advice Generation (Gap to Ideal)
        advice_list = []
        ideal_stats = config_bundle.get("ideal_stats", {})
        
        if ideal_stats:
            # Get current estimated total stats (including echo)
            curr_crit_rate = estimated_stats.get(STAT_CRIT_RATE, 0)
            curr_crit_dmg = estimated_stats.get(STAT_CRIT_DMG, 0)
            # CRITICAL: Adjustment for Wuthering Waves (Display - 100%)
            adj_crit_dmg = max(0, curr_crit_dmg - 100.0)
            
            # 1. Crit Ratio Check (1:2)
            if curr_crit_rate > 5 and adj_crit_dmg > 5:
                if curr_crit_rate > 100.0:
                    effective_rate = 100.0
                    if curr_crit_rate > 105.0:
                        advice_list.append("会心率が100%を大きく超えています。過剰分を会心ダメージ等に振り分けましょう")
                else:
                    effective_rate = curr_crit_rate

                # Ideal DMG should be Rate * 2
                ideal_adj_dmg = effective_rate * 2.0
                if adj_crit_dmg < ideal_adj_dmg * 0.8:
                    advice_list.append("会心ダメージを優先的に稼ぐのが効率的です")
                elif effective_rate < (adj_crit_dmg / 2.0) * 0.8 and effective_rate < 100.0:
                    advice_list.append("会心率をもう少し上げると期待値が伸びます")

            # 2. Stat sufficiency check
            if STAT_ER in ideal_stats and STAT_ER in estimated_stats:
                if estimated_stats[STAT_ER] < ideal_stats[STAT_ER] * 0.9:
                    advice_list.append(f"{STAT_ER}が足りていません（目標: {ideal_stats[STAT_ER]}%）")
            
            if STAT_ATK_PERCENT in ideal_stats and STAT_ATK_PERCENT in estimated_stats:
                if estimated_stats[STAT_ATK_PERCENT] < ideal_stats[STAT_ATK_PERCENT] * 0.8:
                    advice_list.append(f"{STAT_ATK_PERCENT}を稼ぐとダメージが伸びます")

        return EvaluationResult(
            total_score=achievement_rate, 
            effective_count=self.effective_stats_count,
            recommendation="rec_continue" if achievement_rate < 30 else "rec_use",
            rating=rating_key,
            individual_scores=results,
            estimated_stats=estimated_stats,
            consistency_advice=consistency_msg,
            advice_list=advice_list
        )

    def get_rating_by_achievement(self, rate, cost):
        """
        New rating logic based on achievement rate (relative to theoretical max).
        Adjusts thresholds based on cost difficulty.
        """
        # Determine cost difficulty factor
        # Cost 3 is hardest (9 main stats), Cost 4 is medium (5 main stats), Cost 1 is easiest (3 main stats)
        # Note: self.cost might be string like "3" or "4", normalize it.
        c = str(cost)
        
        # Thresholds (Achievement Rate %)
        # Higher achievement is harder for high cost echoes due to farming difficulty.
        # But wait, substats are independent of cost difficulty. 
        # The difficulty is in getting the item. 
        # Once you have the item, a 80% substat roll is just as good on Cost 1 or Cost 3.
        # However, to avoid "げんなり", we can lower the bar for SSS for Cost 3.
        
        if c == "3":
            # Cost 3 is notoriously hard to farm. Give them a break.
            if rate >= 80: return "rating_sss_single"
            if rate >= 65: return "rating_ss_single"
            if rate >= 45: return "rating_s_single"
            if rate >= 25: return "rating_a_single"
        elif c == "4":
            if rate >= 85: return "rating_sss_single"
            if rate >= 70: return "rating_ss_single"
            if rate >= 50: return "rating_s_single"
            if rate >= 30: return "rating_a_single"
        else: # Cost 1 or unknown
            if rate >= 90: return "rating_sss_single"
            if rate >= 75: return "rating_ss_single"
            if rate >= 55: return "rating_s_single"
            if rate >= 35: return "rating_a_single"
            
        if rate >= 15: return "rating_b_single"
        return "rating_c_single"

    def get_rating(self, score):
        """Score evaluation (Community standard)."""
        if score >= 85:
            return "rating_sss_single"
        elif score >= 70:
            return "rating_ss_single"
        elif score >= 50:
            return "rating_s_single"
        elif score >= 30:
            return "rating_a_single"
        elif score >= 20:
            return "rating_b_single"
        else:
            return "rating_c_single"

    def get_rating_normalized(self, score):
        """Normalized score evaluation (0-100 points)."""
        if score >= 70:
            return "rating_sss_norm"
        elif score >= 50:
            return "rating_ss_norm"
        elif score >= 30:
            return "rating_s_norm"
        else:
            return "rating_b_norm"

    def get_rating_ratio(self, score):
        """Ratio score evaluation."""
        if score >= 75:
            return "rating_perf_ratio"
        elif score >= 60:
            return "rating_exc_ratio"
        elif score >= 45:
            return "rating_good_ratio"
        elif score >= 30:
            return "rating_avg_ratio"
        else:
            return "rating_weak_ratio"

    def get_rating_roll(self, score):
        """Roll quality evaluation."""
        if score >= 80:
            return "rating_god_roll"
        elif score >= 65:
            return "rating_win_roll"
        elif score >= 45:
            return "rating_avg_roll"
        else:
            return "rating_bad_roll"

    def get_rating_effective(self, score, eff_count):
        """Effective stats count evaluation."""
        if eff_count >= 5 and score >= 70:
            return ("rating_perf_eff", score)
        elif eff_count >= 4 and score >= 50:
            return ("rating_exc_eff", score)
        elif eff_count >= 3 and score >= 30:
            return ("rating_good_eff", score)
        else:
            return ("rating_bad_eff", eff_count, score)

    def get_rating_cv(self, score):
        """CV (Crit Value) score evaluation - Community Standard."""
        if score >= 45:
            return "rating_outstanding_cv"
        elif score >= 38:
            return "rating_excellent_cv"
        elif score >= 30:
            return "rating_good_cv"
        elif score >= 25:
            return "rating_acceptable_cv"
        else:
            return "rating_weak_cv"

    def to_dict(self):
        """Convert to dictionary format."""
        return {
            "cost": self.cost,
            "main_stat": self.main_stat,
            "substats": self.substats,
            "level": self.level,
            "score": self.score,
            "rating": self.rating,
            "effective_stats_count": self.effective_stats_count
        }

    def get_fingerprint(self) -> str:
        """Generates a unique MD5 fingerprint based on all echo stats."""
        import hashlib
        # Sort substats to ensure consistent hashing
        substats_str = "|".join(f"{k}:{v}" for k, v in sorted(self.substats.items()))
        raw_data = f"{self.cost}|{self.main_stat}|{substats_str}"
        return hashlib.md5(raw_data.encode('utf-8')).hexdigest()

    def __str__(self):
        """String representation."""
        substats_str = "\n".join([
            f"  {name}: {value}" for name, value in self.substats.items()
        ])
        return (
            f"Cost {self.cost} - Level {self.level}\n"
            f"Main: {self.main_stat}\n"
            f"Substats:\n{substats_str}\n"
            f"Score: {self.score:.2f}\n"
            f"Rating: {self.rating}"
        )
