package com.spectraledger.core.repository;

import com.spectraledger.core.domain.Tenant;
import jakarta.persistence.LockModeType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.Optional;
import java.util.UUID;

public interface TenantRepository extends JpaRepository<Tenant, UUID> {

    Optional<Tenant> findByUsername(String username);

    boolean existsByUsername(String username);

    /**
     * Locks the row with SELECT ... FOR UPDATE (Postgres, via Hibernate's PESSIMISTIC_WRITE)
     * for the lifetime of the caller's transaction. Every code path that reads-then-writes a
     * tenant's balance or escrowBalance MUST go through this method, never through the plain
     * findById - see TradeSettlementService and OrderService for the canonical-order locking
     * rule that keeps concurrent trades from deadlocking each other.
     */
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select t from Tenant t where t.id = :id")
    Optional<Tenant> findByIdForUpdate(@Param("id") UUID id);
}
