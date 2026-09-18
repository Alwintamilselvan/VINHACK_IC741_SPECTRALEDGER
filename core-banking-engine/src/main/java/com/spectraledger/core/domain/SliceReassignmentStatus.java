package com.spectraledger.core.domain;

/**
 * State of the (mocked) NSSF slice-reassignment call for a cleared trade. No real RAN/NSSF
 * hardware exists in this demo - this models what a real call to the telecom's network
 * orchestration layer would look like: fire-and-confirm, with realistic latency and a
 * possibility of failure that the platform must handle without corrupting the ledger.
 */
public enum SliceReassignmentStatus {
    PENDING,
    CONFIRMED,
    FAILED
}
