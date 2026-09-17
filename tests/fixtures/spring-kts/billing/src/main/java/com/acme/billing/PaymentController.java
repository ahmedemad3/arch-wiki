package com.acme.billing;

import java.util.List;
import java.util.UUID;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/payments")
@PreAuthorize("hasAuthority('billing.payment.view')")
public class PaymentController {

    @GetMapping
    public List<Object> list() { return List.of(); }

    @GetMapping("/{id}")
    public Object get(@PathVariable UUID id) { return null; }

    @PostMapping("/{id}/refund")
    @PreAuthorize("hasRole('FINANCE')")
    public void refund(@PathVariable UUID id) { }
}
