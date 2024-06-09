#!/bin/sh

if [ "$BUTLARR_INTERACTIVE_SETUP" = "true" ]; then
    # Run interactive setup
    python3 -m butlarr.autosetup
fi

# Continue with the normal entrypoint command
exec "$@"
