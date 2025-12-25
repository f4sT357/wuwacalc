# --- Stat Name Constants (Japanese) ---
STAT_CRIT_RATE = "クリティカル率"
STAT_CRIT_DMG = "クリティカルダメージ"
STAT_ATK_PERCENT = "攻撃力%"
STAT_ATK_FLAT = "攻撃力"
STAT_HP_PERCENT = "HP%"
STAT_HP_FLAT = "HP"
STAT_DEF_PERCENT = "防御力%"
STAT_DEF_FLAT = "防御力"
STAT_ER = "共鳴効率"
STAT_BASIC_DMG_BONUS = "通常攻撃ダメージアップ"
STAT_HEAVY_DMG_BONUS = "重撃ダメージアップ"
STAT_SKILL_DMG_BONUS = "共鳴スキルダメージアップ"
STAT_LIBERATION_DMG_BONUS = "共鳴解放ダメージアップ"
STAT_FUSION_DMG_BONUS = "焦熱ダメージアップ"
STAT_GLACIO_DMG_BONUS = "凝縮ダメージアップ"
STAT_ELECTRO_DMG_BONUS = "電導ダメージアップ"
STAT_AERO_DMG_BONUS = "気動ダメージアップ"
STAT_SPECTRO_DMG_BONUS = "回折ダメージアップ"
STAT_HAVOC_DMG_BONUS = "消滅ダメージアップ"
STAT_HEALING_BONUS = "HP回復効果アップ"

DAMAGE_BONUS_STATS = [
    STAT_BASIC_DMG_BONUS, STAT_HEAVY_DMG_BONUS, 
    STAT_SKILL_DMG_BONUS, STAT_LIBERATION_DMG_BONUS,
    STAT_FUSION_DMG_BONUS, STAT_GLACIO_DMG_BONUS, STAT_ELECTRO_DMG_BONUS,
    STAT_AERO_DMG_BONUS, STAT_SPECTRO_DMG_BONUS, STAT_HAVOC_DMG_BONUS
]

# --- CV Weight Keys ---
CV_KEY_CRIT_RATE = "crit_rate"
CV_KEY_CRIT_DMG = "crit_dmg"
CV_KEY_ATK_PERCENT = "atk_percent"
CV_KEY_ATK_FLAT_DIVISOR = "atk_flat_divisor"
CV_KEY_ATK_FLAT_MULTIPLIER = "atk_flat_multiplier"
CV_KEY_ER = "er"
CV_KEY_DMG_BONUS = "dmg_bonus"

SUBSTAT_MAX_VALUES = {
    "クリティカル率": 10.5, "クリティカルダメージ": 21.0, "攻撃力%": 11.6, "攻撃力": 60,
    "HP%": 11.6, "HP": 580, "防御力%": 11.6, "防御力": 60, "共鳴効率": 12.4,
    "通常攻撃ダメージアップ": 11.6, "重撃ダメージアップ": 11.6, "共鳴スキルダメージアップ": 11.6, "共鳴解放ダメージアップ": 11.6
}

MAIN_STAT_OPTIONS = {
    "4": ["攻撃力%", "HP%", "防御力%", "クリティカル率", "クリティカルダメージ",
          ],
    "3": ["攻撃力%", "HP%", "防御力%", "焦熱ダメージアップ", "凝縮ダメージアップ",
          "電導ダメージアップ", "気動ダメージアップ", "回折ダメージアップ", "消滅ダメージアップ",
          "HP回復効果アップ"],
    "1": ["HP", "攻撃力", "防御力"]
}

MAIN_STAT_MULTIPLIER = 15.0

SUBSTAT_TYPES = {
    "HP": "Flat",
    "HP%": "Percent",
    "攻撃力": "Flat",
    "攻撃力%": "Percent",
    "防御力": "Flat",
    "防御力%": "Percent",
}

CHARACTER_STAT_WEIGHTS = {
    "General": {
    "クリティカル率": 1.0,
    "クリティカルダメージ": 1.0,
    "攻撃力%": 1.0,
    "攻撃力": 0.5,
    "HP%": 0.2,
    "HP": 0.1,
    "防御力%": 0.1,
    "防御力": 0.1,
    "共鳴効率": 0.5,
    "重撃ダメージアップ": 0.5,
    "通常攻撃ダメージアップ": 0.5,
    "共鳴スキルダメージアップ": 0.5,
    "共鳴解放ダメージアップ": 0.5,
    }
}

# --- Weight Templates from Research Report ---
CHARACTER_STAT_WEIGHTS["会心特化型"] = {
    "クリティカル率": 1.0,
    "クリティカルダメージ": 1.0,
    "攻撃力%": 0.9,
    "共鳴効率": 0.7,
    "攻撃力": 0.4,
}

CHARACTER_STAT_WEIGHTS["バランス型"] = {
    "クリティカル率": 1.0,
    "クリティカルダメージ": 1.0,
    "攻撃力%": 0.8,
    "共鳴効率": 0.6,
    "攻撃力": 0.3,
}

CHARACTER_STAT_WEIGHTS["スキル回転型"] = {
    "クリティカル率": 1.0,
    "クリティカルダメージ": 1.0,
    "攻撃力%": 0.8,
    "共鳴効率": 1.0,
    "攻撃力": 0.3,
}

CHARACTER_MAIN_STATS = {
    
    "General": {
        "cost4_echo": "クリティカル率",
        "cost3_echo_1": "攻撃力%",
        "cost3_echo_2": "攻撃力%", 
        "cost1_echo_1": "攻撃力%",
        "cost1_echo_2": "攻撃力%"
    }
}

STAT_ALIASES = {
    "クリティカル率": ["クリティカル率", "クリ率", "クリティカル", "Crit. Rate", "Crit Rate"],
    "クリティカルダメージ": ["クリティカルダメージ", "クリダメ", "クリダメージ", "Crit. DMG", "Crit DMG"],
    "攻撃力%": ["攻撃力%", "攻撃力％", "攻撃力(%)", "攻撃%", "ATK (%)", "ATK%"],
    "攻撃力": ["攻撃力", "ATK", "こうげき"],
    "HP%": ["HP%", "HP％", "HP(%)", "体力%", "HP (%)", "HP%"],
    "HP": ["HP", "体力"],
    "防御力%": ["防御力%", "防御力％", "防御%", "DEF (%)", "DEF%"],
    "防御力": ["防御力", "DEF"],
    "共鳴効率": ["共鳴効率", "効率", "エネルギー効率", "Energy Regen", "Resonance Efficiency"],
    "通常攻撃ダメージアップ": ["通常攻撃ダメージアップ", "通常攻撃up", "通常攻撃ダメージ", "通常ダメージ", "Basic Attack DMG Bonus"],
    "重撃ダメージアップ": ["重撃ダメージアップ", "重撃up", "重撃ダメージ", "Heavy Attack DMG Bonus"],
    "共鳴スキルダメージアップ": ["共鳴スキルダメージアップ", "共鳴スキルup", "スキルダメージ", "Resonance Skill DMG Bonus"],
    "共鳴解放ダメージアップ": ["共鳴解放ダメージアップ", "共鳴解放up", "解放ダメージ", "Resonance Liberation DMG Bonus"],
}

TAB_CONFIGS = {
    "43311": ["cost4_echo", "cost3_echo_1", "cost3_echo_2", "cost1_echo_1", "cost1_echo_2"],
    "44111": ["cost4_echo_1","cost4_echo_2","cost1_echo_1","cost1_echo_2","cost1_echo_3", ],
}

THEME_COLORS = {
    "dark": {
        "background": "#2e2e2e",
        "input_bg": "#202020",
        "text": "#ffffff",
        "shadow": "#000000",
        "border": "#5a5a5a",
        "button_bg": "#5a5a5a",
        "button_text": "#ffffff",
        "button_hover": "#6a6a6a",
        "tab_bg": "#3e3e3e",
        "tab_text": "#ffffff",
        "tab_selected": "#4a90e2",
        "group_border": "#5a5a5a"
    },
    "light": {
        "background": "#f0f0f0",
        "input_bg": "#ffffff",
        "text": "#000000",
        "shadow": "#ffffff",
        "border": "#c0c0c0",
        "button_bg": "#e0e0e0",
        "button_text": "#000000",
        "button_hover": "#d0d0d0",
        "tab_bg": "#e0e0e0",
        "tab_text": "#000000",
        "tab_selected": "#a0c0e0",
        "group_border": "#c0c0c0"
    },
    "clear": {
        "background": "#eefeff",
        "input_bg": "#ffffff",
        "text": "#000000",
        "shadow": "#ffffff",
        "border": "#b0d0e0",
        "button_bg": "#d0efff",
        "button_text": "#000000",
        "button_hover": "#b0e0ff",
        "tab_bg": "#d0efff",
        "tab_text": "#000000",
        "tab_selected": "#80d0ff",
        "group_border": "#b0d0e0"
    },
    "custom": {
        "background": "#2e2e2e",
        "input_bg": "#202020",
        "text": "#ffffff",
        "shadow": "#000000",
        "border": "#5a5a5a",
        "button_bg": "#5a5a5a",
        "button_text": "#ffffff",
        "button_hover": "#6a6a6a",
        "tab_bg": "#3e3e3e",
        "tab_text": "#ffffff",
        "tab_selected": "#4a90e2",
        "group_border": "#5a5a5a"
    }
}

LOG_FILENAME = 'wuwacalc.log'
CONFIG_FILENAME = 'config.json'

# Default cost configuration
DEFAULT_COST_CONFIG = "43311"

# OCR engine constants
OCR_ENGINE_PILLOW = "pillow"
OCR_ENGINE_OPENCV = "opencv"

# JSON key constants for data structures
KEY_SUBSTATS = "substats"
KEY_STAT = "stat"
KEY_VALUE = "value"
KEY_CHARACTER = "character"
KEY_CHARACTER_JP = "character_jp"
KEY_CONFIG = "config"
KEY_AUTO_APPLY = "auto_apply"
KEY_SCORE_MODE = "score_mode"
KEY_ECHOES = "echoes"
KEY_MAIN_STAT = "main_stat"
KEY_CHARACTER_WEIGHTS = "character_weights"
KEY_CHARACTER_MAINSTATS = "character_mainstats"
# --- History Constants ---
ACTION_SINGLE = "Single Evaluation"
ACTION_BATCH = "Batch Evaluation"
ACTION_OCR = "OCR"

# --- UI Constants ---
# Default window dimensions
DEFAULT_WINDOW_WIDTH = 1000
DEFAULT_WINDOW_HEIGHT = 950

# Dialog dimensions
DIALOG_CHAR_SETTING_WIDTH = 600
DIALOG_CHAR_SETTING_HEIGHT = 600
DIALOG_CROP_WIDTH = 900
DIALOG_CROP_HEIGHT = 700

# Image preview dimensions
IMAGE_PREVIEW_MAX_WIDTH = 600
IMAGE_PREVIEW_MAX_HEIGHT = 260

# Timer intervals (milliseconds)
TIMER_SAVE_CONFIG_INTERVAL = 500
TIMER_CROP_PREVIEW_INTERVAL = 100
TIMER_RESIZE_PREVIEW_INTERVAL = 100