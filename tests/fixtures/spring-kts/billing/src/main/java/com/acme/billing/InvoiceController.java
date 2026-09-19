package com.acme.billing;

import java.util.List;
import java.util.UUID;
import org.springframework.http.MediaType;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;

@Tag(name = "Invoices", description = "Invoice lifecycle and lookup")
@RestController
@RequestMapping({"/api/v1/invoices", "/api/v2/invoices"})
public class InvoiceController {

    private final InvoiceRepository invoices;

    public InvoiceController(InvoiceRepository invoices) {
        this.invoices = invoices;
    }

    @Operation(summary = "List invoices for a customer")
    @PreAuthorize("hasAuthority('billing.invoice.view')")
    @GetMapping(produces = MediaType.APPLICATION_JSON_VALUE, path = "/customer/{customerId}")
    public List<Invoice> byCustomer(@PathVariable UUID customerId) {
        return invoices.findByCustomer(customerId);
    }

    @GetMapping(value = {"/{id}", "/by-id/{id}"})
    @PreAuthorize("hasAuthority('billing.invoice.view') and @billingAuth.canAccess(authentication, #id)")
    @Operation(summary = "Get one invoice", description = "Object-level check against the owning customer")
    public Invoice one(@PathVariable UUID id) {
        return invoices.findById(id).orElseThrow();
    }

    @PostMapping
    @PreAuthorize("hasAnyAuthority('billing.invoice.create', 'billing.admin')")
    public Invoice create(@RequestBody Invoice dto) {
        return invoices.save(dto);
    }

    @RequestMapping(value = "/{id}/void", method = {RequestMethod.POST, RequestMethod.PUT}, produces = "application/json")
    public void voidInvoice(@PathVariable UUID id) {
        invoices.voidById(id);
    }
}
