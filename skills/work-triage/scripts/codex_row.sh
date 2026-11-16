#!/bin/bash
# Bash 3.2: arrays keep paths and configuration values as single arguments.
set -u

usage() {
    cat >&2 <<'USAGE'
Usage: codex_row.sh <implement|review|check> --model <codex-model>
       --level <low|medium|high|xhigh> --prompt <file> --out <file>
       [--cd <dir>] [--base <branch> | --uncommitted] [--dry-run]
USAGE
    exit 2
}

fail() {
    printf 'codex_row.sh: %s\n' "$1" >&2
    usage
}

[ "$#" -gt 0 ] || usage
mode=$1
shift
case "$mode" in implement|review|check) ;; *) usage ;; esac
model= level= prompt= out= workdir= base= scope= dry_run=0
while [ "$#" -gt 0 ]; do
    case "$1" in
        --model|--level|--prompt|--out|--cd|--base)
            option=$1
            [ "$#" -ge 2 ] || fail "missing option value"
            [ -n "$2" ] || fail "empty option value"
            case "$2" in --*) fail "missing option value" ;; esac
            case "$option" in
                --model) model=$2 ;;
                --level) level=$2 ;;
                --prompt) prompt=$2 ;;
                --out) out=$2 ;;
                --cd) workdir=$2 ;;
                --base)
                    [ -z "$scope" ] || fail "review scopes are mutually exclusive"
                    scope=base; base=$2 ;;
            esac
            shift 2 ;;
        --uncommitted)
            [ -z "$scope" ] || fail "review scopes are mutually exclusive"
            scope=uncommitted
            shift ;;
        --dry-run) dry_run=1; shift ;;
        -h|--help) usage ;;
        *) fail "unknown argument" ;;
    esac
done
[ -n "$model" ] || fail "--model is required"
case "$level" in low|medium|high|xhigh) ;; *) fail "--level must be low, medium, high or xhigh" ;; esac
[ -n "$prompt" ] || fail "--prompt is required"
[ -f "$prompt" ] && [ -r "$prompt" ] || fail "prompt must be a readable file"
[ -n "$out" ] || fail "--out is required"
[ -z "$workdir" ] || [ -d "$workdir" ] || fail "--cd must be a directory"
[ "$mode" = review ] || [ -z "$scope" ] || fail "scope flags require review"

# Resolve artifact paths before Codex changes its working root.
out_display=$out
case "$prompt" in /*) ;; *) prompt="$PWD/$prompt" ;; esac
case "$out" in /*) ;; *) out="$PWD/$out" ;; esac
sandbox=workspace-write
header=
if [ "$mode" = review ]; then
    sandbox=read-only
    header='Review only; do not edit files or change git state. '
    if [ "$scope" = base ]; then
        printf -v quoted_base '%q' "$base"
        header="${header}Review the branch diff against base $quoted_base (git diff $quoted_base...HEAD). "
    else
        header="${header}Review staged, unstaged, and untracked changes in the working tree. "
    fi
    header="${header}Use the following specification and review instructions:

"
fi

# Enumerate exported names only: secret values never enter diagnostics or argv.
clean_env=(env)
removed=()
while IFS= read -r name; do
    case "$name" in
        OPENAI_API_KEY|CODEX_API_KEY) ;; # Keep Codex CLI API authentication.
        *_KEY|*_TOKEN|*_SECRET)
            clean_env+=( -u "$name" )
            removed+=( "$name" ) ;;
    esac
done < <(compgen -e)
command=(codex exec -m "$model" -c "model_reasoning_effort=\"$level\"" -s "$sandbox")
[ -z "$workdir" ] || command+=( -C "$workdir" )
command+=( -o "$out" - )

if [ "$dry_run" -eq 1 ]; then
    printf 'Removed environment variables:'
    if [ "${#removed[@]}" -eq 0 ]; then
        printf ' (none)'
    else
        printf ' %s' "${removed[@]}"
    fi
    printf '\n'
    if [ -n "$header" ]; then
        printf '{ printf %%s %q; cat -- %q; } | ' "$header" "$prompt"
    fi
    printf '%q ' "${clean_env[@]}" "${command[@]}"
    if [ -z "$header" ]; then
        printf '< %q' "$prompt"
    fi
    printf '\n%s\n' "$out_display"
    exit 0
fi

if [ -n "$header" ]; then
    { printf '%s' "$header"; cat -- "$prompt"; } | "${clean_env[@]}" "${command[@]}"
    result=$?
else
    "${clean_env[@]}" "${command[@]}" < "$prompt"
    result=$?
fi
printf '%s\n' "$out_display"
exit "$result"
