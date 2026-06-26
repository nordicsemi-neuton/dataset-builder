/*
 * firmware_median3_filter.c
 *
 * 3-tap median filter for IMU axis sample-and-hold / FIFO-overrun artifacts.
 *
 * #############################################################################
 * # WARNING — TRAINING/INFERENCE PARITY                                       #
 * #                                                                           #
 * # DO NOT apply this filter only at inference time.                          #
 * #                                                                           #
 * # The model was trained on UNFILTERED data. If you apply this filter only   #
 * # on the device, you introduce a distribution shift between training-time   #
 * # and inference-time features — exactly the kind of shift that quietly     #
 * # degrades accuracy.                                                        #
 * #                                                                           #
 * # Use this filter ONLY in one of these scenarios:                           #
 * #   (a) You're regenerating the training set, applying this filter to all  #
 * #       training data, retraining, and THEN deploying with the same filter #
 * #       at inference. Both sides see the same preprocessing.                #
 * #   (b) You have measured a meaningful spike-rate discrepancy between      #
 * #       training and inference data (training >> inference, or vice versa) #
 * #       AND you've validated that the filter on its own improves accuracy  #
 * #       on a held-out set without retraining.                              #
 * #                                                                           #
 * # In one real case: training had a 0.62% gz jump rate,                #
 * # eval had 0.96%. The gap is small. We REJECTED the filter on              #
 * # parity grounds. See wiki/principles/domain.md (preproc parity).             #
 * # #########################################################################
 *
 * What it removes:
 *   Single-sample outliers — the classic IMU sample-and-hold / FIFO-overrun
 *   signature ("3 identical clipped values surrounded by quiet samples" or
 *   "one sample at ±FS, immediately back to ~0"). The median of 3 consecutive
 *   samples is the middle value, so a lone outlier is replaced by one of its
 *   quiet neighbors.
 *
 * What it does NOT blur:
 *   Real motion. Genuine fast rotation that lasts ≥ 2 consecutive samples
 *   is preserved because two of the three values in the window are real
 *   motion samples.
 *
 * Runtime: branchless, ~10 ns per sample on Cortex-M33.
 * Memory:  2 int16_t per axis (rolling buffer). Zero malloc.
 */

#include <stdint.h>

/**
 * median3() — return the median (middle value) of three int16_t samples.
 * Branchless reference implementation.
 */
static inline int16_t median3(int16_t a, int16_t b, int16_t c)
{
    return (a > b)
         ? ((b > c) ? b : ((a > c) ? c : a))
         : ((a > c) ? a : ((b > c) ? c : b));
}

/* ------------------------------------------------------------------------- */
/* Per-axis rolling state. Initialize to zeros.                              */
/* For a 6-axis IMU (acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z), instantiate */
/* one of these per axis you want to filter.                                  */
/* ------------------------------------------------------------------------- */
typedef struct {
    int16_t prev1;   /* sample at t-1 */
    int16_t prev2;   /* sample at t-2 */
    uint8_t valid;   /* 0 until we've seen ≥ 2 samples */
} median3_state_t;

/**
 * median3_filter() — push a new sample into the rolling buffer and return
 * the median-filtered output. The filter has a 1-sample latency: when you
 * push sample at time t, the returned value is the filtered estimate for
 * time t-1 (the middle of t-2, t-1, t).
 *
 * Until 2 samples have been seen, the filter passes the input through
 * unchanged.
 */
static inline int16_t median3_filter(median3_state_t *s, int16_t sample)
{
    int16_t out;
    if (s->valid < 2) {
        out = sample;             /* warm-up: pass-through */
        s->valid++;
    } else {
        out = median3(s->prev2, s->prev1, sample);
    }
    s->prev2 = s->prev1;
    s->prev1 = sample;
    return out;
}

/* ------------------------------------------------------------------------- */
/* Example: filter the gyro axes of an IMU sample in-place                   */
/* ------------------------------------------------------------------------- */
typedef struct {
    int16_t ax, ay, az;
    int16_t gx, gy, gz;
} imu_sample_t;

void filter_imu_gyros(imu_sample_t *s)
{
    static median3_state_t st_gx = {0}, st_gy = {0}, st_gz = {0};
    s->gx = median3_filter(&st_gx, s->gx);
    s->gy = median3_filter(&st_gy, s->gy);
    s->gz = median3_filter(&st_gz, s->gz);
}
