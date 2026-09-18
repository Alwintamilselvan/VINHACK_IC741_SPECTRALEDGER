package com.spectraledger.core.event;

import com.spectraledger.core.domain.QosTier;

/** Published whenever a resting order is added, filled, partially filled or cancelled in a given matching bucket. */
public record OrderBookChangedEvent(QosTier qosTier, int durationMinutes) {
}
