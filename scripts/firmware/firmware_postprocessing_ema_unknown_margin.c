/*
 * firmware_postprocessing_ema_unknown_margin.c
 *
 * Recommended on-device postprocessing for a Nordic Edge AI Lab multi-class
 * gesture recognition model. Tuned on a real multi-class gesture eval recording
 * (see wiki/synthesis/support-case-patterns.md for the validation numbers).
 *
 * What it does, in order:
 *   1. EMA-smooth the per-class probability vector across consecutive inference
 *      windows. This stabilizes flicker between adjacent windows where the raw
 *      argmax can flip even when the underlying signal is steady.
 *   2. Take argmax on the smoothed vector.
 *   3. Unknown-margin suppression: if the "unknown" class (typically class 1)
 *      wins by only a small margin over the best non-unknown class, prefer the
 *      non-unknown class. The "unknown" class otherwise tends to absorb
 *      borderline gesture detections.
 *
 * What it does NOT do:
 *   - Confidence thresholding (e.g. drop predictions with top-prob < 0.5).
 *     We tested this on real eval data — it consistently hurt accuracy by
 *     dropping legitimate detections. Add it only if a specific false-positive
 *     problem on-device requires it.
 *   - Require-N-consecutive gating. Same reason.
 *   - Event semantics (one event per gesture). This function emits a class
 *     PER INFERENCE WINDOW (state output). For event semantics, wrap a
 *     state-change detector around the output of this function — see comment
 *     at the bottom of this file.
 *
 * Tuning constants (validated on a real multi-class gesture eval recording):
 *   EMA_ALPHA       = 0.3
 *   UNKNOWN_MARGIN  = 0.2
 *   UNKNOWN_CLASS   = 1
 *
 * Performance: ~15 lines of integer/float arithmetic, no malloc, microsecond
 * runtime on a Cortex-M33.
 *
 * Validated accuracy with this pipeline (a real ~50 s eval recording at 100 Hz):
 *   - 79.9% strict window-level accuracy
 *   - 87.2% direction-agnostic accuracy
 *   - 0 false-positive gesture detections during idle/random segments
 */

#include <stdint.h>

/* ------------------------------------------------------------------------- */
/* Tuning constants — change these only if you have ground-truth data to    */
/* validate the alternative values.                                         */
/* ------------------------------------------------------------------------- */
#define NUM_CLASSES      8
#define EMA_ALPHA        0.3f
#define UNKNOWN_MARGIN   0.2f
#define UNKNOWN_CLASS    1   /* class index treated as "unknown" / catch-all */

/* ------------------------------------------------------------------------- */
/* Persistent EMA state. Initialize to zeros; do NOT reset between          */
/* inference windows.                                                        */
/* ------------------------------------------------------------------------- */
static float ema_probs[NUM_CLASSES] = {0.0f};

/**
 * postprocess() — apply the recommended postprocessing to a single inference
 * window's raw class probabilities and return the recommended class.
 *
 * @param raw_probs  array of NUM_CLASSES float probabilities (the
 *                   p_model->decoded_output.classif.probabilities.p_f32 from
 *                   the nRF EdgeAI runtime).
 * @param out_class  the recommended class for this window (0..NUM_CLASSES-1).
 *
 * Call once per inference, e.g. after every nrf_edgeai_run_inference()
 * success. With window=100 and shift=30 at 100 Hz, this is called every
 * ~333 ms.
 */
void postprocess(const float raw_probs[NUM_CLASSES], uint8_t *out_class)
{
    /* 1. EMA-smooth the probability vector across time. */
    for (int i = 0; i < NUM_CLASSES; i++) {
        ema_probs[i] = EMA_ALPHA * raw_probs[i]
                     + (1.0f - EMA_ALPHA) * ema_probs[i];
    }

    /* 2. Argmax on the smoothed vector. */
    int top = 0;
    for (int i = 1; i < NUM_CLASSES; i++) {
        if (ema_probs[i] > ema_probs[top]) {
            top = i;
        }
    }

    /* 3. Unknown-margin suppression: if "unknown" is the top class but its
     *    lead over the best non-unknown class is small, prefer the non-unknown
     *    class. This stops "unknown" from absorbing real gestures sitting on
     *    the decision boundary. */
    if (top == UNKNOWN_CLASS) {
        int alt = (UNKNOWN_CLASS == 0) ? 1 : 0;
        for (int i = 0; i < NUM_CLASSES; i++) {
            if (i == UNKNOWN_CLASS) continue;
            if (ema_probs[i] > ema_probs[alt]) {
                alt = i;
            }
        }
        if (ema_probs[top] - ema_probs[alt] < UNKNOWN_MARGIN) {
            top = alt;
        }
    }

    *out_class = (uint8_t)top;
}

/* ------------------------------------------------------------------------- */
/* OPTIONAL: layer this state-change event detector on top of postprocess() */
/* if you want one event per user gesture instead of per-window state.      */
/* ------------------------------------------------------------------------- */
/*
 *  static uint8_t last_class = UNKNOWN_CLASS;
 *  static int     quiet_count = 0;
 *  #define MIN_QUIET_WINDOWS 3
 *
 *  void emit_event_if_transition(uint8_t this_class, void (*fire)(uint8_t)) {
 *      const int is_quiet = (this_class == 0 || this_class == UNKNOWN_CLASS);
 *
 *      if (is_quiet) {
 *          quiet_count++;
 *          if (quiet_count >= MIN_QUIET_WINDOWS) {
 *              last_class = this_class;
 *          }
 *          return;
 *      }
 *
 *      // We're in a gesture class. Fire ONLY if we transitioned from quiet
 *      // OR from a different gesture class.
 *      if (this_class != last_class) {
 *          fire(this_class);
 *          last_class = this_class;
 *      }
 *      quiet_count = 0;
 *  }
 */
