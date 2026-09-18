package com.spectraledger.core.repository;

import com.spectraledger.core.domain.Trade;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.UUID;

public interface TradeRepository extends JpaRepository<Trade, Long> {

    List<Trade> findTop50ByOrderByClearedAtDesc();

    @Query("select t from Trade t where t.buyerTenant.id = :tenantId or t.sellerTenant.id = :tenantId order by t.clearedAt desc")
    List<Trade> findByTenantIdOrderByClearedAtDesc(@Param("tenantId") UUID tenantId);
}
