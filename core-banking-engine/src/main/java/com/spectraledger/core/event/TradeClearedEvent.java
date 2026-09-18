package com.spectraledger.core.event;

import com.spectraledger.core.domain.Trade;

/**
 * Published by TradeSettlementService AFTER its transaction commits (via
 * @TransactionalEventListener(phase = AFTER_COMMIT) listeners), never before. This is the
 * in-process substitute for a Kafka "trade.cleared" topic: same decoupling of "the trade
 * happened" from "everyone who cares about it reacts", zero extra infrastructure. Swapping in
 * a real broker later means adding a listener that republishes this event, not touching the
 * settlement code at all.
 */
public record TradeClearedEvent(Trade trade) {
}
