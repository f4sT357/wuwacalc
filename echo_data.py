from constants import (
    STAT_CRIT_RATE, STAT_CRIT_DMG, STAT_ATK_PERCENT, STAT_ATK_FLAT, STAT_ER,
    CV_KEY_CRIT_RATE, CV_KEY_CRIT_DMG, CV_KEY_ATK_PERCENT, 
    CV_KEY_ATK_FLAT_DIVISOR, CV_KEY_ATK_FLAT_MULTIPLIER, CV_KEY_ER, CV_KEY_DMG_BONUS,
    DAMAGE_BONUS_STATS
)
from data_contracts import EvaluationResult

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

    def calculate_score_cv_based(self, stat_weights, cv_weights):
        """Method 5: CV (Crit Value) Based Method - Community Standard"""
        cv_score = 0.0
        
        # Basic CV calculation (most important)
        crit_rate = self.substats.get(STAT_CRIT_RATE, 0)
        crit_dmg = self.substats.get(STAT_CRIT_DMG, 0)
        
        cv_score += (crit_rate * cv_weights.get(CV_KEY_CRIT_RATE, 2.0)) + \
                    (crit_dmg * cv_weights.get(CV_KEY_CRIT_DMG, 1.0))
        
        # Extended scoring with other valuable stats
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

    def evaluate_comprehensive(self, character_weights, config_bundle, enabled_methods=None):
        """Comprehensive evaluation using provided configuration.
        
        Args:
            character_weights: Dictionary of stat weights for the character
            config_bundle: Dictionary containing all configuration data (max_values, multipliers, etc.)
            enabled_methods: Dictionary of {method_name: bool} indicating which methods to use.
        """
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
            results["cv"] = self.calculate_score_cv_based(
                character_weights, config_bundle.get("cv_weights", {})
            )
        
        # Calculate average score from enabled methods
        if results:
            avg_score = sum(results.values()) / len(results)
        else:
            avg_score = 0.0
        
        return EvaluationResult(
            total_score=avg_score,
            effective_count=self.effective_stats_count,
            recommendation="rec_continue" if avg_score < 30 else "rec_use",
            rating=self.get_rating(avg_score),
            individual_scores=results
        )

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
