if [ -f /etc/bash.bashrc ]; then
    . /etc/bash.bashrc
fi

# A bare `exit` means the user is done, not that Make should repeat the status
# of the last exploratory command. Explicit statuses such as `exit 7` survive.
exit() {
    if [ "$#" -eq 0 ]; then
        builtin exit 0
    fi
    builtin exit "$@"
}
