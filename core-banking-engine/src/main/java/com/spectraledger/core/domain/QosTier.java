package com.spectraledger.core.domain;

/** Quality-of-service tier for a leased slice of 5G bandwidth. Orders only match within the same tier. */
public enum QosTier {
    BRONZE,
    SILVER,
    GOLD,
    PLATINUM
}
