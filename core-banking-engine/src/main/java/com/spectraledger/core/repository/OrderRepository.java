package com.spectraledger.core.repository;

import com.spectraledger.core.domain.Order;
import com.spectraledger.core.domain.OrderStatus;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface OrderRepository extends JpaRepository<Order, Long> {

    List<Order> findByTenantIdOrderByCreatedAtDesc(UUID tenantId);

    Optional<Order> findByIdAndTenantId(Long id, UUID tenantId);

    /** Used once, at startup, to rebuild the in-memory order book from durable storage. */
    List<Order> findByStatusIn(List<OrderStatus> statuses);
}
