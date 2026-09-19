package com.acme.billing;

import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface InvoiceRepository extends JpaRepository<Invoice, UUID> {

    @Query("SELECT i FROM Invoice i JOIN i.customer c WHERE c.id = :customerId")
    List<Invoice> findByCustomer(@Param("customerId") UUID customerId);

    @Query(value = """
        SELECT inv.*, cust.name
        FROM billing.invoice inv
        JOIN billing.customer cust ON cust.id = inv.customer_id
        WHERE inv.status = :status
        """, nativeQuery = true)
    List<Object[]> findWithCustomerByStatus(@Param("status") String status);

    @Modifying
    @Query(value = "UPDATE billing.invoice SET status = 'VOID' WHERE id = :id", nativeQuery = true)
    int voidById(@Param("id") UUID id);
}
