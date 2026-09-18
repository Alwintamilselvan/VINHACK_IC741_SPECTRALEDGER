package com.spectraledger.core.service;

import com.spectraledger.core.domain.LedgerEntry;
import com.spectraledger.core.dto.LedgerChainVerificationResponse;
import com.spectraledger.core.repository.LedgerEntryRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

/**
 * Walks the ENTIRE ledger table from the genesis entry and recomputes every hash from the raw
 * column values, comparing it against what was actually stored. This is the live, on-demand
 * proof that the audit trail is tamper-evident: if anyone ever ran
 *   UPDATE ledger_entries SET balance_after = ... WHERE id = 42
 * directly against the database, that row's recomputed hash would no longer match its stored
 * entryHash (and/or the next row's previousEntryHash would no longer match it), and this
 * service reports exactly which entry broke the chain instead of just saying "something's wrong".
 */
@Service
@RequiredArgsConstructor
public class LedgerChainVerificationService {

    private final LedgerEntryRepository ledgerEntryRepository;

    @Transactional(readOnly = true)
    public LedgerChainVerificationResponse verify() {
        List<LedgerEntry> entries = ledgerEntryRepository.findAllByOrderByIdAsc();

        String expectedPrevious = "GENESIS";

        for (LedgerEntry entry : entries) {
            if (!expectedPrevious.equals(entry.getPreviousEntryHash())) {
                return new LedgerChainVerificationResponse(
                        false, entries.size(), entry.getId(),
                        "Entry " + entry.getId() + " records previousEntryHash="
                                + entry.getPreviousEntryHash() + " but the chain up to that point actually computes to "
                                + expectedPrevious + " - the chain is broken or was reordered.");
            }

            String recomputed = LedgerHashUtil.hash(
                    expectedPrevious,
                    entry.getTenant().getId(),
                    entry.getTrade().getId(),
                    entry.getEntryType(),
                    entry.getAmount(),
                    entry.getBalanceAfter(),
                    entry.getDescription());

            if (!recomputed.equals(entry.getEntryHash())) {
                return new LedgerChainVerificationResponse(
                        false, entries.size(), entry.getId(),
                        "Entry " + entry.getId() + "'s stored hash does not match its own data - "
                                + "this row was modified after it was written.");
            }

            expectedPrevious = entry.getEntryHash();
        }

        return new LedgerChainVerificationResponse(
                true, entries.size(), null,
                "All " + entries.size() + " ledger entries verified - the chain is intact from genesis to tip.");
    }
}
