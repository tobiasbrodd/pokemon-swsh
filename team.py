from pokemon import Pokemon, Type, Stats
from getopt import getopt, GetoptError
import pandas as pd
import numpy as np
import sys


def load():
    pokemon = pd.read_csv("data/pokemon.csv", sep=",")
    pokemon.fillna("", inplace=True)

    rows = pokemon.shape[0]
    for row in range(rows):
        type_1 = pokemon.loc[row, "type_1"]
        type_2 = pokemon.loc[row, "type_2"]

        if len(type_2) > 0 and type_2 < type_1:
            pokemon.loc[row, "type_1"] = type_2
            pokemon.loc[row, "type_2"] = type_1

    return pokemon


def filter_pokemon(
    pokemon,
    stats,
    stage=None,
    only_final=False,
    allow_legendary=True,
    allow_mythical=True,
):
    pokemon = pokemon[pokemon["hp"] > stats[Stats.HP]]
    pokemon = pokemon[pokemon["attack"] > stats[Stats.ATTACK]]
    pokemon = pokemon[pokemon["defense"] > stats[Stats.DEFENSE]]
    pokemon = pokemon[pokemon["sp_attack"] > stats[Stats.SP_ATTACK]]
    pokemon = pokemon[pokemon["sp_defense"] > stats[Stats.SP_DEFENSE]]
    pokemon = pokemon[pokemon["speed"] > stats[Stats.SPEED]]

    if stage is not None:
        pokemon = pokemon[pokemon["stage"] == stage]
    if only_final:
        pokemon = pokemon[pokemon["is_final"] == 1]
    if not allow_legendary:
        pokemon = pokemon[pokemon["is_legendary"] == 0]
    if not allow_mythical:
        pokemon = pokemon[pokemon["is_mythical"] == 0]

    return pokemon


def get_types(pokemon):
    lookup = {}
    types = list(zip(pokemon.type_1, pokemon.type_2))
    types = list(set(types))

    return types


def generate_weakness_chart(pokemon):
    types = get_types(pokemon)
    indices = {}
    weaknesses = []
    for (i, t) in enumerate(types):
        type_1 = t[0]
        type_2 = t[1]
        fltr = np.logical_and(pokemon.type_1 == type_1, pokemon.type_2 == type_2)
        pkmn = pokemon.loc[fltr].head(1).to_numpy()
        weaknesses.append(pkmn[:, 14:].reshape(-1,))
        indices[t] = i

    all_types = pokemon.columns[14:]
    weaknesses = np.asmatrix(weaknesses)
    weaknesses = pd.DataFrame(weaknesses, index=types, columns=all_types)

    return weaknesses, types


def generate_team_types(weaknesses, types, size=6):
    team_types = []
    weaknesses -= 1
    chart = weaknesses

    for i in range(size):
        perf = np.sum(chart, axis=1)
        best = np.argmin(perf)
        t = types[best]
        team_types.append(t)
        chart = update_chart(weaknesses, chart, t, best)

    return team_types


def update_chart(weaknesses, chart, t, best):
    type_1 = t[0]
    type_2 = t[1]

    m, n = weaknesses.shape

    update = chart * 0

    type_weaknesses = weaknesses.iloc[best, :]
    min_weakness = np.amin(type_weaknesses)
    weak_types = type_weaknesses[type_weaknesses == min_weakness]
    fltr = np.logical_and(weak_types.index != type_1, weak_types.index != type_2)
    update_types = weak_types.loc[fltr]
    update.iloc[best, :][update_types.index] += 2

    type_weaknesses = weaknesses.iloc[best, :]
    max_weaknesses = np.amax(type_weaknesses)
    strong_types = type_weaknesses[type_weaknesses == max_weaknesses].index
    effective = weaknesses[strong_types]
    update_indices = []
    update_types = []
    for row in range(m):
        weakness_types = effective.columns[(effective.iloc[row, :] < 0).values]
        e_type_1 = effective.index[row][0]
        e_type_2 = effective.index[row][1]
        not_in_strong_types = (e_type_1 not in strong_types) and (
            e_type_2 not in strong_types
        )
        if len(weakness_types) > 0 and not_in_strong_types:
            update_indices.append(row)
            update_types.append(weakness_types)

    for i in range(len(update_indices)):
        index = update_indices[i]
        weakness_types = update_types[i]
        update.iloc[index, :][weakness_types] -= 1

    chart = chart.add(update)

    return chart


def get_team(pokemon, team_types, weights=None):
    team = []

    if weights is None:
        stats = pokemon.columns[8:14]
        weights = pd.DataFrame(np.ones((1, 6)), columns=stats)

    for t in team_types:
        type_1 = t[0]
        type_2 = t[1]
        fltr = np.logical_and(pokemon.type_1 == type_1, pokemon.type_2 == type_2)
        pkmns = pokemon.loc[fltr]
        stats = pkmns.iloc[:, 8:14]
        weighted_stats = stats.multiply(weights.to_numpy())
        index = weighted_stats.sum(axis=1).idxmax(axis=0)
        pkmn = pkmns.loc[index]
        team.append(frame_to_pokemon(pkmn))

    return team


def get_random_team(pokemon, size=6):
    n = pokemon.shape[0]
    rdx = np.random.randint(0, n, size)
    pkmns = pokemon.iloc[rdx, :]

    team = []
    rows = pkmns.shape[0]
    for row in range(rows):
        team.append(frame_to_pokemon(pkmns.iloc[row, :]))

    return team


def frame_to_pokemon(frame):
    no = frame["no"]
    name = frame["name"]
    type_1 = frame["type_1"]
    type_2 = frame["type_2"]
    types = [Type[type_1.upper()], None if len(type_2) <= 0 else Type[type_2.upper()]]
    stats = {
        Stats.HP: frame["hp"],
        Stats.ATTACK: frame["attack"],
        Stats.DEFENSE: frame["defense"],
        Stats.SP_ATTACK: frame["sp_attack"],
        Stats.SP_DEFENSE: frame["sp_defense"],
        Stats.SPEED: frame["speed"],
    }
    weaknesses = frame[14:]
    stage = frame["stage"]
    is_final = frame["is_final"]
    is_legendary = frame["is_legendary"]
    is_mythical = frame["is_mythical"]

    pokemon = Pokemon(
        no,
        name,
        types,
        stats,
        weaknesses,
        stage=stage,
        is_final=is_final,
        is_legendary=is_legendary,
        is_mythical=is_mythical,
    )

    return pokemon


def main(argv):
    short_options = "h"
    long_options = [
        "help",
        "size=",
        "hp=",
        "attack=",
        "defense=",
        "spattack=",
        "spdefense=",
        "speed=",
        "weights=",
        "stage=",
        "final",
        "legendary",
        "mythical",
        "random",
    ]
    help_message = """usage: run.py [options]
    options:
        -h, --help          Prints help message.
        --size s            Sets size of the team to 's'. Default: '6'.
        --hp h              Sets minimum HP to 'h'. Default: '0'.
        --attack a          Sets minimum attack to 'a'. Default: '0'.
        --defense d         Sets minimum defense to 'd'. Default: '0'.
        --spattack s        Sets minimum sp. attack to 's'. Default: '0'.
        --spdefense s       Sets minimum sp. defense to 's'. Default: '0'.
        --speed s           Sets minimum speed to 's'. Default: '0'.
        --weights w         Sets weights to 'w'. Default: '1,1,1,1,1,1'.
        --stage s           Sets stage to 'ws'. Default: 'None'.
        --final             Only allows final evolutions.
        --legendary         Don't allow legendary Pokemon.
        --mytical           Don't allow mythical Pokemon.
        --random            Randomizes team generation."""

    try:
        opts, args = getopt(argv, shortopts=short_options, longopts=long_options)
    except GetoptError:
        print(help_message)
        return

    size = 6
    min_hp = 0
    min_attack = 0
    min_defense = 0
    min_sp_attack = 0
    min_sp_defense = 0
    min_speed = 0
    weights = np.ones((1, 6))
    stage = None
    only_final = False
    allow_legendary = True
    allow_mythical = True
    randomize = False

    for opt, arg in opts:
        if opt in ["-h", "--help"]:
            print(help_message)
            return
        elif opt == "--size":
            size = int(arg)
        elif opt == "--hp":
            min_hp = float(arg)
        elif opt == "--attack":
            min_attack = float(arg)
        elif opt == "--defense":
            min_defense = float(arg)
        elif opt == "--spattack":
            min_sp_attack = float(arg)
        elif opt == "--spdefense":
            min_sp_defense = float(arg)
        elif opt == "--speed":
            min_speed = float(arg)
        elif opt == "--weights":
            weights = np.asmatrix([float(w) for w in arg.split(",")])
        elif opt == "--stage":
            stage = int(arg)
        elif opt == "--final":
            only_final = True
        elif opt == "--legendary":
            allow_legendary = False
        elif opt == "--mythical":
            allow_mythical = False
        elif opt == "--random":
            randomize = True

    if weights.shape[1] != 6:
        print(help_message)
        return
    elif stage < 1 or stage > 3:
        print(help_message)
        return

    min_stats = {
        Stats.HP: min_hp,
        Stats.ATTACK: min_attack,
        Stats.DEFENSE: min_defense,
        Stats.SP_ATTACK: min_sp_attack,
        Stats.SP_DEFENSE: min_sp_defense,
        Stats.SPEED: min_speed,
    }

    pokemon = load()
    pokemon = filter_pokemon(
        pokemon,
        min_stats,
        stage=stage,
        only_final=only_final,
        allow_legendary=allow_legendary,
        allow_mythical=allow_mythical,
    )

    team = []
    if randomize:
        team = get_random_team(pokemon, size=size)
    else:
        weaknesses, types = generate_weakness_chart(pokemon)
        team_types = generate_team_types(weaknesses, types, size=size)

        stats = pokemon.columns[8:14]
        weights = pd.DataFrame(weights, columns=stats)
        team = get_team(pokemon, team_types, weights=weights)

    stats = np.zeros((len(team),))
    for (i, p) in enumerate(team):
        stats[i] = p.get_total_stat()
    print(f"Team: {[p.name for p in team]}")
    print(f"Mean Total: {stats.mean():.2f}")


if __name__ == "__main__":
    main(sys.argv[1:])
