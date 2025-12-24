from languages import TRANSLATIONS
from data_contracts import EvaluationResult, EchoEntry

class HtmlRenderer:
    """Class responsible for generating HTML for score results."""
    
    def __init__(self, tr_func, lang: str):
        """
        Initialization
        
        Args:
            tr_func: Translation function (app.tr).
            lang: Current application language.
        """
        self.tr = tr_func
        self.language = lang

    def _get_rating_color(self, rating_text: str) -> str:
        """Get the appropriate color from the rating text."""
        if any(keyword in rating_text for keyword in ["SSS", "Perfect", "God"]):
            return "#FF4500"
        elif any(keyword in rating_text for keyword in ["SS", "Top", "Excellent"]):
            return "#FF7F50"
        elif any(keyword in rating_text for keyword in ["S", "Win"]):
            return "#1E90FF"
        elif any(keyword in rating_text for keyword in ["A", "Good", "Practical"]):
            return "#32CD32"
        return "#666666"

    def render_single_score(self, character: str, tab_name: str, entry: EchoEntry, main_stat: str, echo: any, evaluation: EvaluationResult) -> str:
        """Generate HTML for single score result."""
        html = f"<h3><u>{character} - {tab_name} {self.tr('individual_score_title')}</u></h3>"
        html += f"<hr>"
        
        html += f"<b>{self.tr('echo_info')}</b><br>"
        html += f"{self.tr('cost')}: {entry.cost}<br>"
        html += f"{self.tr('main_stat')}: {self.tr(main_stat)}<br>"
        html += f"{self.tr('level')}: {echo.level}<br>"
        html += f"{self.tr('effective_stats_num')}: {evaluation.effective_count}<br>"
        
        html += f"<br><b>{self.tr('substats')}</b><br>"
        substats = echo.substats
        if substats:
            for name, value in substats.items():
                html += f"&nbsp;&nbsp;• {self.tr(name)}: {value}<br>"
        else:
            html += f"{self.tr('none')}<br>"
        html += f"<br><hr>"
        
        html += f"<b>{self.tr('score_by_method')}</b><br>"
        
        def format_score_block(label, score, rating_info, desc):
            block = f"[{label}]<br>"
            block += f"<b>Score: {score:.2f}</b><br>"
            
            if isinstance(rating_info, tuple):
                rating_key = rating_info[0]
                rating_args = rating_info[1:]
                rating_text = TRANSLATIONS.get(self.language, TRANSLATIONS["en"])[rating_key].format(*rating_args)
            else:
                rating_text = TRANSLATIONS.get(self.language, TRANSLATIONS["en"])[rating_info]

            color = self._get_rating_color(rating_text)
            block += f"<span style='color:{color}'>Rating: {rating_text}</span><br>"
            block += f"Description: {desc}<br><br>"
            return block

        # Method information
        method_info = {
            "normalized": {
                "label": self.tr("normalized_score_label"),
                "desc": self.tr("normalized_score_desc"),
                "rating_func": lambda s: echo.get_rating_normalized(s)
            },
            "ratio": {
                "label": self.tr("ratio_score_label"),
                "desc": self.tr("ratio_score_desc"),
                "rating_func": lambda s: echo.get_rating_ratio(s)
            },
            "roll": {
                "label": self.tr("roll_quality_label"),
                "desc": self.tr("roll_quality_desc"),
                "rating_func": lambda s: echo.get_rating_roll(s)
            },
            "effective": {
                "label": self.tr("effective_stat_label"),
                "desc": self.tr("effective_stat_desc"),
                "rating_func": lambda s: echo.get_rating_effective(s, evaluation.effective_count)
            },
            "cv": {
                "label": self.tr("cv_score_label"),
                "desc": self.tr("cv_score_desc"),
                "rating_func": lambda s: echo.get_rating_cv(s)
            }
        }
        
        # Display only enabled methods
        for method, score in evaluation.individual_scores.items():
            if method in method_info:
                info = method_info[method]
                rating = info["rating_func"](score)
                html += format_score_block(info["label"], score, rating, info["desc"])

        html += f"<hr>"
        html += f"<b>{self.tr('overall_eval')}</b><br>"
        html += f"<b>{self.tr('total_score')}: {evaluation.total_score:.2f}</b><br>"
        
        final_rating = self.tr(evaluation.rating)
        final_color = self._get_rating_color(final_rating)
        
        html += f"<span style='color:{final_color}'>{self.tr('overall_rating')}: {final_rating}</span><br>"
        html += f"{self.tr('recommendation')}: {self.tr(evaluation.recommendation)}<br>"
        
        return html

    def render_batch_score(self, character: str, calculated_count: int, total_count: int, all_evaluations: list, total_scores: dict, enabled_methods: dict) -> str:
        """Generate HTML for batch score result."""
        html = f"<h3><u>{character} {self.tr('batch_score_title')}</u></h3>"
        html += f"<hr>"
        html += f"{self.tr('calculated')}: {calculated_count} / {total_count} echoes<br>"
        html += f"<hr>"
        
        # Method display info
        method_labels = {
            "normalized": self.tr("method_normalized"),
            "ratio": self.tr("method_ratio"),
            "roll": self.tr("method_roll"),
            "effective": self.tr("method_effective"),
            "cv": self.tr("method_cv")
        }
        
        for i, eval_data in enumerate(all_evaluations, 1):
            html += f"<b>--- Echo {i}: {eval_data['tab_name']} ---</b><br>"
            
            method_num = 1
            for method in ["normalized", "ratio", "roll", "effective", "cv"]:
                if enabled_methods.get(method, False) and method in eval_data:
                    score = eval_data[method]
                    label = method_labels.get(method, method)
                    
                    if method == "effective":
                        html += f"├ [{method_num}] {label}: {score:.2f} ({eval_data['effective_count']} stats)<br>"
                    else:
                        html += f"├ [{method_num}] {label}: {score:.2f}<br>"
                    method_num += 1
            
            score_color = "#666666" 
            if eval_data['total'] >= 85: score_color = "#FF4500" 
            elif eval_data['total'] >= 70: score_color = "#FF7F50" 
            elif eval_data['total'] >= 50: score_color = "#1E90FF" 
            elif eval_data['total'] >= 30: score_color = "#32CD32" 
            
            html += f"└ <b><span style='color:{score_color}'>{self.tr('total_score')}: {eval_data['total']:.2f}</span></b><br>"
            html += f"&nbsp;&nbsp;{self.tr('recommendation')}: {eval_data['recommendation']}<br><br>"
        
        html += f"<hr>"
        html += f"<b>{self.tr('avg_scores_title')} ({calculated_count} echoes)</b><br>"
        
        for method in ["normalized", "ratio", "roll", "effective", "cv"]:
            if enabled_methods.get(method, False) and method in total_scores:
                avg = total_scores[method] / calculated_count
                label = method_labels.get(method, method)
                html += f"├ {label} {self.tr('average')}: {avg:.2f}<br>"
        
        total_sum = total_scores["total"]
        avg_total = total_sum / calculated_count
        avg_rating_key = self._get_score_rating_key(avg_total)
        avg_rating_text = self.tr(avg_rating_key)
        avg_color = self._get_rating_color(avg_rating_text)
        
        html += f"├ <b>{self.tr('total_sum')}: {total_sum:.2f}</b><br>"
        html += f"├ <b><span style='color:{avg_color}'>{self.tr('total_average')}: {avg_total:.2f}</span></b><br>"
        html += f"└ <span style='color:{avg_color}'>{self.tr('overall_rating')}: {avg_rating_text}</span><br>"
        
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
