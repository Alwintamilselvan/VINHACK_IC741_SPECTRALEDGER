package com.spectraledger.core.service;

import com.spectraledger.core.domain.LedgerEntry;
import com.spectraledger.core.domain.NetworkSlice;
import com.spectraledger.core.domain.Tenant;
import com.spectraledger.core.domain.Trade;
import com.spectraledger.core.exception.ResourceNotFoundException;
import com.spectraledger.core.repository.LedgerEntryRepository;
import com.spectraledger.core.repository.NetworkSliceRepository;
import com.spectraledger.core.repository.TenantRepository;
import com.spectraledger.core.repository.TradeRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class AccountService {

    private final TenantRepository tenantRepository;
    private final NetworkSliceRepository sliceRepository;
    private final LedgerEntryRepository ledgerEntryRepository;
    private final TradeRepository tradeRepository;

    public Tenant getTenant(UUID tenantId) {
        return tenantRepository.findById(tenantId)
                .orElseThrow(() -> new ResourceNotFoundException("Tenant not found: " + tenantId));
    }

    public List<NetworkSlice> getSlices(UUID tenantId) {
        return sliceRepository.findByTenantId(tenantId);
    }

    public List<LedgerEntry> getLedgerHistory(UUID tenantId) {
        return ledgerEntryRepository.findByTenantIdOrderByCreatedAtDesc(tenantId);
    }

    public List<Trade> getTradeHistory(UUID tenantId) {
        return tradeRepository.findByTenantIdOrderByClearedAtDesc(tenantId);
    }
}
