package com.spectraledger.core.dto;

import java.math.BigDecimal;

public record OrderBookLevel(
        BigDecimal price,
        int totalQuantityMbps,
        int orderCount
) {
}
