package com.spectraledger.core.repository;

import com.spectraledger.core.domain.NetworkSlice;
import jakarta.persistence.LockModeType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface NetworkSliceRepository extends JpaRepository<NetworkSlice, UUID> {

    List<NetworkSlice> findByTenantId(UUID tenantId);

    /** Same SELECT ... FOR UPDATE contract as TenantRepository#findByIdForUpdate, applied to slice capacity. */
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select s from NetworkSlice s where s.id = :id")
    Optional<NetworkSlice> findByIdForUpdate(@Param("id") UUID id);
}
