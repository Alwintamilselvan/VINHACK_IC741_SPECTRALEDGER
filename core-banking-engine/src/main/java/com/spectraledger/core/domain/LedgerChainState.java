package com.spectraledger.core.domain;

import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

/**
 * Singleton (always id = 1L) pointer to the tip of the ledger's hash chain - see LedgerEntry
 * and TradeSettlementService for how the chain itself is built. Appending to the ledger locks
 * this one row (SELECT ... FOR UPDATE) first, which is what makes the chain a true linear
 * sequence even when trades for unrelated tenant pairs are settling concurrently: without this,
 * two concurrent trades could both read the same "current tip" and each append believing they
 * followed it, silently forking the chain.
 */
@Entity
@Table(name = "ledger_chain_state")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class LedgerChainState {

    @Id
    private Long id;

    private String lastEntryHash;

    public static LedgerChainState genesis() {
        return LedgerChainState.builder().id(1L).lastEntryHash("GENESIS").build();
    }
}
