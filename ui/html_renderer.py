from utils.languages import TRANSLATIONS
from core.data_contracts import EvaluationResult, EchoEntry
from utils.constants import STAT_CRIT_RATE, STAT_CRIT_DMG, STAT_ATK_PERCENT, STAT_ER

class HtmlRenderer:
    """Class responsible for generating HTML for score results."""
    
    def __init__(self, tr_func, lang: str, show_shadow: bool = True, shadow_color: str = "#000000", text_color: str = "#333333", 
                 shadow_ox: float = 2.0, shadow_oy: float = 2.0, shadow_blur: float = 5.0, shadow_spread: float = 0.0):
        """
        Initialization
        
        Args:
            tr_func: Translation function (app.tr).
            lang: Current application language.
            show_shadow: Whether to show text shadows.
            shadow_color: Hex color string for the shadow.
            text_color: Hex color string for the main text.
            shadow_ox: Offset X.
            shadow_oy: Offset Y.
            shadow_blur: Blur radius.
            shadow_spread: Spread radius (simulated).
        """
        self.tr = tr_func
        self.language = lang
        self.show_shadow = show_shadow
        self.shadow_color = shadow_color
        self.text_color = text_color
        self.shadow_ox = shadow_ox
        self.shadow_oy = shadow_oy
        self.shadow_blur = shadow_blur
        self.shadow_spread = shadow_spread
        self._update_common_style()

    def set_shadow_params(self, ox: float, oy: float, blur: float, spread: float):
        """Update shadow parameters and refresh style."""
        self.shadow_ox = ox
        self.shadow_oy = oy
        self.shadow_blur = blur
        self.shadow_spread = spread
        self._update_common_style()

    def set_show_shadow(self, show: bool):
        """Update the shadow setting and refresh common style."""
        self.show_shadow = show
        self._update_common_style()

    def set_shadow_color(self, color: str):
        """Update the shadow color and refresh common style."""
        self.shadow_color = color
        self._update_common_style()

    def set_text_color(self, color: str):
        """Update the text color and refresh common style."""
        self.text_color = color
        self._update_common_style()

    def _update_common_style(self):
        """Updates the internal CSS style based on current settings."""
        
        def hex_to_rgba(hex_color, alpha):
            hex_color = hex_color.lstrip('#')
            try:
                r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
                return f"rgba({r}, {g}, {b}, {alpha})"
            except ValueError:
                return "rgba(0,0,0,0.5)"

        if self.show_shadow:
            bg_color = hex_to_rgba(self.shadow_color, 0.5)
            border_px = max(1, int(self.shadow_spread))
            border_style = f"{border_px}px solid {hex_to_rgba(self.shadow_color, 0.3)}"
        else:
            bg_color = "rgba(255, 255, 255, 0.15)"
            border_style = "1px solid rgba(128, 128, 128, 0.2)"

        self.common_style = f"""
        <!-- STYLE_START -->
        <style>
            body {{ 
                font-family: 'Segoe UI', sans-serif; 
                line-height: 1.4; 
                color: {self.text_color};
            }}
            h3 {{ color: {self.text_color}; margin-bottom: 5px; }}
            hr {{ border: 0; border-top: 1px solid #ccc; margin: 10px 0; }}
            .score-block {{
                margin-bottom: 12px; 
                padding: 8px;
                border-radius: 6px;
                background-color: {bg_color};
                border: {border_style};
            }}
            .outline, .dark-outline {{
                font-weight: bold;
                background-color: {bg_color};
                border-radius: 3px;
                padding: 0 2px;
            }}
        </style>
        <!-- STYLE_END -->
        """

    def _get_rating_color(self, rating_text: str) -> str:
        """Get the appropriate color from the rating text."""
        if any(keyword in rating_text for keyword in ["SSS", "Perfect", "God"]):
            return "#FF4500" # OrangeRed
        elif any(keyword in rating_text for keyword in ["SS", "Top", "Excellent"]):
            return "#E67E22" # Carrot
        elif any(keyword in rating_text for keyword in ["S", "Win"]):
            return "#2980B9" # Belize Hole
        elif any(keyword in rating_text for keyword in ["A", "Good", "Practical"]):
            return "#27AE60" # Nephritis
        return "#7F8C8D" # Asbestos

    def format_score_block(self, label, score, rating_info, desc):
        """Helper to format a single method score block."""
        if isinstance(rating_info, tuple):
            rating_key = rating_info[0]
            rating_args = rating_info[1:]
            rating_text = self.tr(rating_key, *rating_args)
        else:
            rating_text = self.tr(rating_info)

        color = self._get_rating_color(rating_text)
        
        block = f"<div class='score-block'>"
        block += f"<b>[{label}]</b><br>"
        block += f"<b>Score: {score:.2f}</b><br>"
        block += f"<span style='color:{color}; font-weight: bold;'>Rating: {rating_text}</span><br>"
        block += f"<small><i>{desc}</i></small>"
        block += f"</div>"
        return block

    def render_single_score(self, character: str, tab_name: str, entry: EchoEntry, main_stat: str, echo: any, evaluation: EvaluationResult) -> str:
        """Generate HTML for single score result."""
        title = self.tr('individual_score_title', character, tab_name).replace('\n', '')
        html = self.common_style
        html += f"<h3><u>{title}</u></h3>"
        html += f"<hr>"
        
        # New: Display consistency advice
        if evaluation.consistency_advice:
            html += f"<div style='color: #ff5555; background: rgba(255,0,0,0.1); padding: 5px; border-left: 3px solid #ff5555; margin-bottom: 10px;'>"
            html += f"⚠️ {evaluation.consistency_advice}</div>"

        # New: Display build optimization advice
        if evaluation.advice_list:
            html += "<div style='margin-bottom: 10px; font-size: 0.95em; color: #88ccff; background: rgba(0,0,0,0.2); padding: 5px; border-radius: 4px;'>"
            for advice in evaluation.advice_list:
                html += f"• {advice}<br>"
            html += "</div>"
        
        html += f"<b>{self.tr('echo_info').replace('\n', '')}</b><br>"
        html += f"&nbsp;&nbsp;• {self.tr('cost')}: {entry.cost}<br>"
        html += f"&nbsp;&nbsp;• {self.tr('main_stat')}: {self.tr(main_stat)}<br>"
        html += f"&nbsp;&nbsp;• {self.tr('level', echo.level).replace('\n', '')}<br>"
        html += f"&nbsp;&nbsp;• {self.tr('effective_substat_count', evaluation.effective_count).replace('\n', '')}<br>"
        
        html += f"<br><b>{self.tr('substats').replace('\n', '')}</b><br>"
        substats = echo.substats
        if substats:
            for name, value in substats.items():
                html += f"&nbsp;&nbsp;&nbsp;&nbsp;{self.tr(name)}: {value}<br>"
        else:
            html += f"&nbsp;&nbsp;{self.tr('none').replace('\n', '')}<br>"
        html += f"<hr>"
        
        html += f"<b>{self.tr('score_by_method').replace('\n', '')}</b><br>"
        
        # Method information
        method_info = {
            "achievement": {
                "label": self.tr("achievement_rate_label"),
                "desc": self.tr("achievement_rate_desc"),
                "rating_func": lambda s: evaluation.rating
            },
            "normalized": {
                "label": self.tr("method_normalized"),
                "desc": self.tr("normalized_score_desc"),
                "rating_func": lambda s: echo.get_rating_normalized(s)
            },
            "ratio": {
                "label": self.tr("method_ratio"),
                "desc": self.tr("ratio_score_desc"),
                "rating_func": lambda s: echo.get_rating_ratio(s)
            },
            "roll": {
                "label": self.tr("method_roll"),
                "desc": self.tr("roll_quality_desc"),
                "rating_func": lambda s: echo.get_rating_roll(s)
            },
            "effective": {
                "label": self.tr("method_effective"),
                "desc": self.tr("effective_stat_desc"),
                "rating_func": lambda s: echo.get_rating_effective(s, evaluation.effective_count)
            },
            "cv": {
                "label": self.tr("method_cv"),
                "desc": self.tr("cv_score_desc"),
                "rating_func": lambda s: echo.get_rating_cv(s)
            }
        }
        
        methods_to_show = list(evaluation.individual_scores.keys())
        if "achievement" in methods_to_show:
            methods_to_show.remove("achievement")
            methods_to_show.insert(0, "achievement")

        for method in methods_to_show:
            if method in method_info:
                score = evaluation.individual_scores[method]
                info = method_info[method]
                rating = info["rating_func"](score)
                html += self.format_score_block(info["label"], score, rating, info["desc"])

        html += f"<hr>"
        
        if evaluation.estimated_stats:
            html += f"<b>{self.tr('estimated_total_stats').replace('\n', '')}</b><br>"
            priority = [STAT_CRIT_RATE, STAT_CRIT_DMG, STAT_ATK_PERCENT, STAT_ER]
            
            for sname in priority:
                if sname in evaluation.estimated_stats:
                    val = evaluation.estimated_stats[sname]
                    html += f"&nbsp;&nbsp;• {self.tr(sname)}: {val:.1f}<br>"
            
            for sname, val in sorted(evaluation.estimated_stats.items()):
                if sname not in priority and val > 0 and not sname.startswith(("Total ", "Goal ")):
                    html += f"&nbsp;&nbsp;• {self.tr(sname)}: {val:.1f}<br>"
            
            for sname, val in evaluation.estimated_stats.items():
                if sname.startswith("Total "):
                    html += f"<br><b>&nbsp;&nbsp;{sname}: {val:.1f}</b><br>"
                if sname.startswith("Goal "):
                    html += f"<b>&nbsp;&nbsp;{sname}: {val:.1f}%</b><br>"
            
            # Adjustment for Crit Ratio Check logic inside HTML rendering if necessary
            # The current app might use these values for something.
            # Here we just display. 
            
            html += f"<hr>"

        html += f"<b>{self.tr('overall_eval').replace('\n', '')}</b><br>"
        html += f"<b>{self.tr('achievement_rate_label')}: {evaluation.total_score:.2f}%</b><br>"
        
        final_rating = self.tr(evaluation.rating)
        final_color = self._get_rating_color(final_rating)
        
        html += f"<span style='color:{final_color}; font-size: 1.2em;'><b>{self.tr('overall_rating')}: {final_rating}</b></span><br>"
        
        if evaluation.comparison_diff is not None:
            diff = evaluation.comparison_diff
            diff_color = "#32CD32" if diff >= 0 else "#FF4500"
            sign = "+" if diff >= 0 else ""
            html += f"<b class='outline' style='color:{diff_color}; font-size: 1.1em;'>{self.tr('vs_equipped')}: {sign}{diff:.2f}%</b><br>"

        html += f"{self.tr('recommendation')}: {self.tr(evaluation.recommendation)}<br>"
        
        return html

    def render_batch_score(self, character: str, calculated_count: int, total_count: int, all_evaluations: list, total_scores: dict, enabled_methods: dict) -> str:
        """Generate HTML for batch score result."""
        batch_title = self.tr('batch_score_title', character).replace('\n', '')
        html = self.common_style
        html += f"<h3><u>{batch_title}</u></h3>"
        html += f"<b>{self.tr('calculated', calculated_count, total_count).replace('\n', '')}</b><br>"
        html += f"<hr>"
        
        method_labels = {
            "normalized": self.tr("method_normalized"),
            "ratio": self.tr("method_ratio"),
            "roll": self.tr("method_roll"),
            "effective": self.tr("method_effective"),
            "cv": self.tr("method_cv")
        }
        
        for i, eval_data in enumerate(all_evaluations, 1):
            html += f"<b>--- {self.tr('echo_n_header', i, eval_data['tab_name']).strip()} ---</b><br>"
            
            for method in ["normalized", "ratio", "roll", "effective", "cv"]:
                if enabled_methods.get(method, False) and method in eval_data:
                    score = eval_data[method]
                    label = method_labels.get(method, method)
                    if method == "effective":
                        html += f"&nbsp;&nbsp;├ {label}: {score:.2f} ({eval_data['effective_count']} stats)<br>"
                    else:
                        html += f"&nbsp;&nbsp;├ {label}: {score:.2f}<br>"
            
            score_color = "#666666" 
            if eval_data['total'] >= 85: score_color = "#FF4500" 
            elif eval_data['total'] >= 70: score_color = "#E67E22" 
            elif eval_data['total'] >= 50: score_color = "#2980B9" 
            elif eval_data['total'] >= 30: score_color = "#27AE60" 
            
            html += f"&nbsp;&nbsp;└ <b><span style='color:{score_color}'>{self.tr('total_score')}: {eval_data['total']:.2f}</span></b><br>"
            html += f"&nbsp;&nbsp;&nbsp;&nbsp;<small>{self.tr('recommendation')}: {eval_data['recommendation']}</small><br><br>"
        
        html += f"<hr>"
        html += f"<b>{self.tr('avg_scores_title', calculated_count).replace('\n', '')}</b><br>"
        
        for method in ["normalized", "ratio", "roll", "effective", "cv"]:
            if enabled_methods.get(method, False) and method in total_scores:
                avg = total_scores[method] / calculated_count
                label = method_labels.get(method, method)
                html += f"&nbsp;&nbsp;├ {label} {self.tr('average')}: {avg:.2f}<br>"
        
        total_sum = total_scores["total"]
        avg_total = total_sum / calculated_count
        avg_rating_key = self._get_score_rating_key(avg_total)
        avg_rating_text = self.tr(avg_rating_key)
        avg_color = self._get_rating_color(avg_rating_text)
        
        html += f"&nbsp;&nbsp;├ {self.tr('total_sum')}: {total_sum:.2f}<br>"
        html += f"&nbsp;&nbsp;├ <b><span style='color:{avg_color}'>{self.tr('total_average')}: {avg_total:.2f}</span></b><br>"
        html += f"&nbsp;&nbsp;└ <span style='color:{avg_color}; font-size: 1.1em;'><b>{self.tr('overall_rating')}: {avg_rating_text}</b></span><br>"
        
        return html

    def _get_score_rating_key(self, avg_score: float) -> str:
        """Get the rating key for the average score (matches 20/30/50/70/85 standard)."""
        if avg_score >= 85:
            return "rating_sss_global"
        elif avg_score >= 70:
            return "rating_ss_global"
        elif avg_score >= 50:
            return "rating_s_global"
        elif avg_score >= 30:
            return "rating_a_global"
        elif avg_score >= 20:
            return "rating_b_global"
        else:
            return "rating_c_global"
