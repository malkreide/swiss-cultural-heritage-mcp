#!/usr/bin/env bash
# SessionStart-Hook: meldet zwei Dinge, die stillschweigend schieflaufen.
#
#   1. Wie viele Commits der ausgecheckte Stand hinter origin/<Standard-Branch>
#      liegt. Bei 0 schweigt er.
#   2. Dass `core.hooksPath` nicht auf .githooks zeigt, die versionierten
#      git-Hooks dieses Klons also nicht laufen. Zeigt es dorthin, schweigt er.
#
# Die zweite Pruefung braucht kein Netz und haengt nicht an einem Remote. Sie
# steht darum in einer eigenen Funktion und laeuft auch dort, wo die erste
# aussteigt -- ein Klon ohne `origin` hat denselben nicht installierten Hook.
#
# GRUND
# -----
# Am 3.8.2026 hat ein veralteter Klon hier zweimal eine rote CI erzeugt, deren
# Ursache nicht im Diff stand: die fehlenden Commits waren jeweils genau die,
# die das Gate einfuehrten, an dem der Branch scheiterte. Gesucht wurde beide
# Male in den falschen Dateien. Die Pruefung kostet eine Sekunde und ersetzt
# diese Fehlersuche.
#
# ABSOLUTER VORRANG: DIESER HOOK BLOCKIERT NIE
# --------------------------------------------
# Ein Hook, der bei Netzproblemen die Arbeit anhaelt, wird nach dem zweiten Mal
# abgeschaltet und schuetzt danach gar nichts. Darum:
#   * KEIN `set -e` / `set -u` / `set -o pipefail`. Das ist Absicht, nicht
#     vergessen: unter `set -e` beendet der erste fehlschlagende git-Aufruf das
#     Skript mit dessen Exit-Code, und ein Exit != 0 aus einem SessionStart-Hook
#     wird als Fehler gemeldet statt still verworfen.
#   * Der gesamte Ablauf steckt in `pruefe`; die letzte Zeile ist `exit 0`.
#     Egal was drinnen passiert, die Session startet.
#   * Jeder Netzaufruf laeuft unter einem Zeitlimit (Default 5s, s. u.).
#   * Kein Aufruf darf nach Zugangsdaten fragen -> GIT_TERMINAL_PROMPT=0 usw.
#   * stderr geht nach /dev/null; stdout traegt ausschliesslich die Meldung.
#
# Still durchgehen sollen unter anderem: kein git, kein Repo, kein `origin`,
# leeres Repo ohne Commit, detached HEAD, DNS-Aussetzer, haengendes Netz,
# geloeschter Standard-Branch.
#
# STANDARD-BRANCH WIRD ERMITTELT, NICHT ANGENOMMEN
# ------------------------------------------------
# Im Portfolio heissen drei Server ihren Standard-Branch `master`
# (openlex-mcp, swiss-courts-mcp, swisstopo-mcp). Die Annahme "main" hat dort
# schon einmal einen Branch 15 Commits alt werden lassen, weil `git fetch
# origin main` mit "couldn't find remote ref main" abbrach und das wie ein
# Netzproblem aussah. Quelle ist darum `git ls-remote --symref origin HEAD`.
#
# ABSCHALTEN: CLAUDE_SKIP_FRESHNESS_CHECK=1 (Aktualitaet),
#             CLAUDE_SKIP_HOOKS_CHECK=1 (hooksPath). Je eine Variable pro
#             Pruefung, weil eine Sammelvariable namens ...FRESHNESS... ueber
#             die hooksPath-Meldung gelogen haette. Wer FRESHNESS=1 gesetzt
#             hatte, um Ruhe zu haben, sieht die neue Zeile also -- und kann
#             sie mit der zweiten Variablen ebenso abstellen.
# ZEITLIMIT:  CLAUDE_FRESHNESS_TIMEOUT=<Sekunden> setzen.

readonly ZEITLIMIT="${CLAUDE_FRESHNESS_TIMEOUT:-5}"

# Fuehrt "$@" mit Zeitlimit aus. `timeout` ist coreutils und auf macOS ohne
# Homebrew-coreutils nicht da (dort ggf. `gtimeout`); der letzte Zweig kommt
# ohne beides aus, damit das Limit nirgends still entfaellt -- ein ungekapptes
# `git fetch` in einem haengenden Netz ist genau der Fall, den dieser Hook
# nicht verursachen darf.
mit_zeitlimit() {
    if command -v timeout > /dev/null 2>&1; then
        timeout -k 2 "$ZEITLIMIT" "$@"
        return $?
    fi
    if command -v gtimeout > /dev/null 2>&1; then
        gtimeout -k 2 "$ZEITLIMIT" "$@"
        return $?
    fi
    "$@" &
    local pid=$! gewartet=0
    while kill -0 "$pid" 2> /dev/null; do
        if [ "$gewartet" -ge "$ZEITLIMIT" ]; then
            kill -TERM "$pid" 2> /dev/null
            sleep 1
            kill -KILL "$pid" 2> /dev/null
            wait "$pid" 2> /dev/null
            return 124
        fi
        sleep 1
        gewartet=$((gewartet + 1))
    done
    wait "$pid"
}

pruefe() {
    [ "${CLAUDE_SKIP_FRESHNESS_CHECK:-}" = "1" ] && return 0

    cd "${CLAUDE_PROJECT_DIR:-.}" 2> /dev/null || return 0
    command -v git > /dev/null 2>&1 || return 0
    git rev-parse --git-dir > /dev/null 2>&1 || return 0
    # Leeres Repo: HEAD zeigt auf einen Branch ohne Commit. `rev-list` haette
    # hier keinen Startpunkt.
    git rev-parse --verify --quiet HEAD > /dev/null 2>&1 || return 0
    git remote get-url origin > /dev/null 2>&1 || return 0

    # Niemals interaktiv werden: ohne diese Variablen wartet git bei einem
    # privaten Remote ohne Credential-Helper auf eine Eingabe, die im
    # Sessionstart niemand sieht -- und haengt bis ins Zeitlimit.
    export GIT_TERMINAL_PROMPT=0
    export GIT_ASKPASS=/bin/echo
    export SSH_ASKPASS=/bin/echo
    export SSH_ASKPASS_REQUIRE=never
    export GIT_SSH_COMMAND="${GIT_SSH_COMMAND:-ssh -o BatchMode=yes -o ConnectTimeout=5}"

    # Ein einziger Aufruf liefert beides: den Namen des Standard-Branches und
    # die SHA seiner Spitze. `ls-remote` uebertraegt keine Objekte, ist also
    # deutlich billiger als ein `fetch` -- und im Normalfall (Klon aktuell)
    # bleibt es bei diesem einen Aufruf.
    local symref
    symref="$(mit_zeitlimit git ls-remote --symref origin HEAD 2> /dev/null)" || return 0

    local branch spitze
    branch="$(printf '%s\n' "$symref" | sed -n 's|^ref: refs/heads/\([^[:space:]]*\)[[:space:]]*HEAD$|\1|p' | head -n 1)"
    spitze="$(printf '%s\n' "$symref" | sed -n 's|^\([0-9a-f]\{7,\}\)[[:space:]]*HEAD$|\1|p' | head -n 1)"
    [ -n "$branch" ] || return 0
    [ -n "$spitze" ] || return 0

    # Kennt der Klon die Spitze schon, ist kein Netz mehr noetig.
    if ! git cat-file -e "${spitze}^{commit}" 2> /dev/null; then
        mit_zeitlimit git fetch --quiet --no-tags origin "$branch" > /dev/null 2>&1 || return 0
        git cat-file -e "${spitze}^{commit}" 2> /dev/null || return 0
    fi

    local fehlend
    fehlend="$(git rev-list --count "HEAD..${spitze}" 2> /dev/null)" || return 0
    case "$fehlend" in
        '' | 0 | *[!0-9]*) return 0 ;;
    esac

    local commit_wort="Commits"
    [ "$fehlend" = "1" ] && commit_wort="Commit"

    cat << MELDUNG
Klon-Aktualitaet: der ausgecheckte Stand liegt ${fehlend} ${commit_wort} hinter
origin/${branch} (${spitze}).

Das ist eine Meldung, keine Blockade. Sie steht hier, weil ein veralteter Klon
am 3.8.2026 zweimal eine rote CI erzeugt hat, deren Ursache nicht im Diff
stand: es fehlten genau die Commits, die das Gate einfuehrten, an dem der
Branch scheiterte. Vor laengerer Arbeit oder beim Deuten eines roten Gates
zuerst aktualisieren:

    git fetch origin ${branch} && git merge --ff-only origin/${branch}

Wer bewusst auf einem aelteren Stand arbeitet, ignoriert das hier.
MELDUNG
}

# Gibt es in $1 etwas, das git ueberhaupt ausfuehren koennte?
#
# Gefragt wird nach einer ausfuehrbaren regulaeren Datei, nicht nach
# `pre-commit`: Ein fester Name deckte einen spaeter dazukommenden `pre-push`
# nicht, und `-d .githooks` allein wuerde auch ueber einem Verzeichnis mit
# bloss einer README meckern. Das Ausfuehrungsrecht ist genau die Bedingung,
# unter der git einen Hook startet -- und `README.md` ist nicht ausfuehrbar,
# es braucht also keine handgeschriebene Ausnahmeliste.
#
# Preis dieser Wahl: Verliert ein Hook sein +x, schweigt diese Meldung, obwohl
# dann gar nichts laeuft. Diesen Fall haelt
# `tests/test_pre_commit_hook.py::test_ausfuehrungsrecht_steht_auch_im_index`
# in der CI, nicht der Sessionstart.
hooks_vorhanden() {
    local eintrag
    for eintrag in "$1"/*; do
        [ -f "$eintrag" ] && [ -x "$eintrag" ] && return 0
    done
    return 1
}

pruefe_hooks_pfad() {
    [ "${CLAUDE_SKIP_HOOKS_CHECK:-}" = "1" ] && return 0

    cd "${CLAUDE_PROJECT_DIR:-.}" 2> /dev/null || return 0
    command -v git > /dev/null 2>&1 || return 0

    # Die Wurzel, nicht das aktuelle Verzeichnis: `.githooks` liegt oben, und
    # git loest ein relatives `core.hooksPath` ebenfalls von dort auf. In einem
    # bare-Repo scheitert der Aufruf -- dort gibt es nichts zu melden.
    local wurzel
    wurzel="$(git rev-parse --show-toplevel 2> /dev/null)" || return 0
    [ -n "$wurzel" ] || return 0

    # Kein .githooks mit ausfuehrbarem Inhalt: Dieses Repo liefert keine
    # versionierten Hooks aus, also ist auch nichts zu installieren. Das haelt
    # die Meldung von jedem anderen Repo des Portfolios fern, in das dieser
    # Hook kopiert wird.
    hooks_vorhanden "$wurzel/.githooks" || return 0

    # `--path` expandiert `~` so, wie git es beim Ausfuehren tut; der rohe Wert
    # liesse `~/repo/.githooks` als fremden Pfad erscheinen.
    local gesetzt
    gesetzt="$(git config --path --get core.hooksPath 2> /dev/null)"

    # Verglichen werden Verzeichnisse, nicht Zeichenketten. Nachgemessen am
    # 28.10.2026 mit git 2.43: git fuehrt den Hook bei `.githooks`,
    # `./.githooks`, `.githooks/` und dem absoluten Pfad gleichermassen aus,
    # und loest relativ gegen die Wurzel auf. Ein Stringvergleich kannte davon
    # zwei und meldete bei den anderen -- bei jedem Sessionstart einen
    # Fehlalarm, also genau das, was eine Meldung abschaltbar macht. Das
    # `cd` aus der Wurzel bildet die Aufloesung von git nach, `pwd -P` loest
    # dazu Symlinks auf.
    #
    # Laesst sich `gesetzt` nicht aufloesen, ist `ist` leer und ungleich
    # `soll` -- das wird gemeldet, nicht verschluckt: Ein Pfad, auf den kein
    # `cd` geht, fuehrt git auch nicht aus. `soll` selbst ist hier nie leer,
    # das hat `hooks_vorhanden` oben schon sichergestellt.
    if [ -n "$gesetzt" ]; then
        local ist soll
        ist="$(cd "$wurzel" 2> /dev/null && cd "$gesetzt" 2> /dev/null && pwd -P)"
        soll="$(cd "$wurzel/.githooks" 2> /dev/null && pwd -P)"
        [ "$ist" = "$soll" ] && return 0
    fi

    local lage
    if [ -z "$gesetzt" ]; then
        lage="\`core.hooksPath\` ist in diesem Klon nicht gesetzt"
    else
        lage="\`core.hooksPath\` zeigt auf ${gesetzt}, nicht auf .githooks"
    fi

    cat << MELDUNG
Git-Hooks nicht aktiv: ${lage}.
Die versionierten Hooks in .githooks/ laufen damit nicht. Einmal pro Klon:

    git config core.hooksPath .githooks

Danach lehnt der pre-commit-Hook einen Commit ab, in dem die Version und eine
Stelle, die sie wiederholt, auseinanderstehen -- etwa ein Bump ohne
regenerierten Tool-Pin. Begruendung: .githooks/README.md.

Diese Zeile steht hier, weil \`core.hooksPath\` pro Klon gilt und nicht
versionierbar ist: Ein Hook, den niemand installiert, schuetzt nichts. Nicht
gewollt? CLAUDE_SKIP_HOOKS_CHECK=1 setzen.
MELDUNG
}

pruefe
pruefe_hooks_pfad
# Bedingungslos: der Rueckgabewert der Pruefungen darf den Sessionstart nicht
# erreichen. Diese Zeile ist die eigentliche Zusicherung des Hooks.
exit 0
