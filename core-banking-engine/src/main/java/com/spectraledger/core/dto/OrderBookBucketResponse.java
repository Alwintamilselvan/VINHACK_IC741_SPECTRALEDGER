package com.spectraledger.core.dto;

import com.spectraledger.core.domain.QosTier;

import java.util.List;

/**
 * One matching bucket's book: bids sorted best (highest) price first, asks sorted best
 * (lowest) price first - exactly the order the matching engine itself scans in.
 */
public record OrderBookBucketResponse(
        QosTier qosTier,
        int durationMinutes,
        List<OrderBookLevel> bids,
        List<OrderBookLevel> asks
) {
}
