package com.spectraledger.core.repository;

import com.spectraledger.core.domain.LedgerEntry;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.UUID;

public interface LedgerEntryRepository extends JpaRepository<LedgerEntry, Long> {

    List<LedgerEntry> findByTenantIdOrderByCreatedAtDesc(UUID tenantId);

    /** Used by AdminController#verifyChain to walk the whole ledger in the exact order it was appended. */
    List<LedgerEntry> findAllByOrderByIdAsc();
}
