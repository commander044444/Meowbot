# ==========================================
# 🐱 MeowBot - Battle System
# ==========================================

import random

from database import (
    create_user,
    get_user,
    get_gym_level,
    add_meow_coins,
)


# ==========================================
# Rewards
# ==========================================

WIN_REWARD = 20
LOSE_REWARD = 5


# ==========================================
# Battle Calculation
# ==========================================

def calculate_battle(
    attacker_level,
    defender_level
):

    attacker_level = int(attacker_level)
    defender_level = int(defender_level)

    # --------------------------------------
    # Equal Level
    # --------------------------------------

    if attacker_level == defender_level:

        attacker_chance = 0.50

    # --------------------------------------
    # Attacker Stronger
    # --------------------------------------

    elif attacker_level > defender_level:

        attacker_chance = 0.80

    # --------------------------------------
    # Defender Stronger
    # --------------------------------------

    else:

        attacker_chance = 0.20

    roll = random.random()

    attacker_wins = (
        roll < attacker_chance
    )

    return {
        "attacker_wins": attacker_wins,
        "attacker_chance": attacker_chance,
        "roll": roll,
    }


# ==========================================
# Start Battle
# ==========================================

def start_battle(
    attacker_id,
    defender_id,
    chat_id=None,
):

    attacker_id = int(attacker_id)
    defender_id = int(defender_id)

    # --------------------------------------
    # Self Battle
    # --------------------------------------

    if attacker_id == defender_id:

        return {
            "success": False,
            "reason": "self_battle",
        }

    # --------------------------------------
    # Chat ID
    # --------------------------------------

    if chat_id is None:
        chat_id = "global"

    chat_id = str(chat_id)

    # --------------------------------------
    # Create Users
    # --------------------------------------

    attacker = get_user(
        attacker_id,
        chat_id
    )

    if not attacker:

        create_user(
            user_id=attacker_id,
            chat_id=chat_id,
            first_name="Unknown",
            username=""
        )

        attacker = get_user(
            attacker_id,
            chat_id
        )

    defender = get_user(
        defender_id,
        chat_id
    )

    if not defender:

        create_user(
            user_id=defender_id,
            chat_id=chat_id,
            first_name="Unknown",
            username=""
        )

        defender = get_user(
            defender_id,
            chat_id
        )

    # --------------------------------------
    # Names
    # --------------------------------------

    attacker_name = (
        attacker["first_name"]
        or "Unknown"
    )

    defender_name = (
        defender["first_name"]
        or "Unknown"
    )

    # --------------------------------------
    # Gym Levels
    # --------------------------------------

    attacker_level = get_gym_level(
        attacker_id,
        chat_id
    )

    defender_level = get_gym_level(
        defender_id,
        chat_id
    )

    # --------------------------------------
    # Calculate
    # --------------------------------------

    battle = calculate_battle(
        attacker_level=attacker_level,
        defender_level=defender_level
    )

    # --------------------------------------
    # Winner / Loser
    # --------------------------------------

    if battle["attacker_wins"]:

        winner_id = attacker_id
        loser_id = defender_id

        winner_name = attacker_name
        loser_name = defender_name

    else:

        winner_id = defender_id
        loser_id = attacker_id

        winner_name = defender_name
        loser_name = attacker_name

    # --------------------------------------
    # Rewards
    # --------------------------------------

    add_meow_coins(
        user_id=winner_id,
        chat_id=chat_id,
        amount=WIN_REWARD
    )

    add_meow_coins(
        user_id=loser_id,
        chat_id=chat_id,
        amount=LOSE_REWARD
    )

    # --------------------------------------
    # Result
    # --------------------------------------

    return {
        "success": True,
        "reason": "battle_finished",

        "attacker_id": attacker_id,
        "defender_id": defender_id,

        "attacker_name": attacker_name,
        "defender_name": defender_name,

        "attacker_level": attacker_level,
        "defender_level": defender_level,

        "winner_id": winner_id,
        "loser_id": loser_id,

        "winner_name": winner_name,
        "loser_name": loser_name,

        "winner_reward": WIN_REWARD,
        "loser_reward": LOSE_REWARD,

        "attacker_chance": battle[
            "attacker_chance"
        ],

        "roll": battle["roll"],
    }