package com.spectraledger.core.repository;

import com.spectraledger.core.domain.LedgerChainState;
import jakarta.persistence.LockModeType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.Optional;

public interface LedgerChainStateRepository extends JpaRepository<LedgerChainState, Long> {

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select c from LedgerChainState c where c.id = :id")
    Optional<LedgerChainState> findByIdForUpdate(@Param("id") Long id);
}
