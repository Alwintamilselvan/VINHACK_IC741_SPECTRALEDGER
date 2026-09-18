package com.spectraledger.core.event;

import com.spectraledger.core.domain.Trade;

/** Published once the mocked NSSF slice-reassignment call for a trade resolves (confirmed or failed). */
public record ReassignmentUpdatedEvent(Trade trade) {
}
