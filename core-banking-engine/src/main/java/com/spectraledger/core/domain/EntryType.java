package com.spectraledger.core.domain;

/** Direction of a double-entry ledger line. Every trade produces exactly one DEBIT and one CREDIT of equal amount. */
public enum EntryType {
    DEBIT,
    CREDIT
}
