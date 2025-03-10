#include <dolphin.h>
#include <dolphin/os.h>

static void (* ResetCallback)();
static int Down;
static long long Hold;

void __OSResetSWInterruptHandler() {
    void (* callback)();
    int unused;

    Down = 1;
    OS_PI_INTR_CAUSE[0] = 2;
    __OSMaskInterrupts(0x200);

    if (ResetCallback) {
        callback = ResetCallback;
        ResetCallback = NULL;
        callback();
    }
}

void (* OSSetResetCallback(void (* callback)()))() {
    int enabled;
    void (* prevCallback)();

    enabled = OSDisableInterrupts();
    prevCallback = ResetCallback;
    ResetCallback = callback;

    if (callback) {
        OS_PI_INTR_CAUSE[0] = 2;
        __OSUnmaskInterrupts(0x200);
    } else {
        __OSMaskInterrupts(0x200);
    }
    OSRestoreInterrupts(enabled);
    return prevCallback;
}

int OSGetResetSwitchState() {
    int enabled;
    int state;
    unsigned long reg;

    enabled = OSDisableInterrupts();
    reg = OS_PI_INTR_CAUSE[0];

    if (!(reg & 0x10000)) {
        Down = 1;
        state = 1;
    } else if (Down != 0) {
        if (reg & 2) {
            OS_PI_INTR_CAUSE[0] = 2;
            Down = 1;
        } else {
            Down = 0;
            Hold = __OSGetSystemTime();
        }
        state = 1;
    } else if (Hold && (__OSGetSystemTime() - Hold) < OSMillisecondsToTicks(50)) {
        state = 1;
    } else {
        state = 0;
        Hold = 0;
    }
    OSRestoreInterrupts(enabled);
    return state;
}
