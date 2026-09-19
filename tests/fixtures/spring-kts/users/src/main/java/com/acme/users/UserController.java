package com.acme.users;

import java.security.Principal;
import java.util.List;
import java.util.UUID;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping(path = "/api/v1/users", produces = "application/json")
public class UserController {

    @GetMapping
    @PreAuthorize("isAuthenticated()")
    public Page<Object> list(Pageable pageable) { return Page.empty(); }

    @GetMapping("/me")
    public Object me(Principal principal) { return principal; }

    @DeleteMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public void delete(@PathVariable UUID id) { }

    @PatchMapping(path = "/{id}/roles", consumes = "application/json")
    @PreAuthorize("@userAuth.isSelfOrAdmin(#id)")
    public Object roles(@PathVariable UUID id, @RequestBody List<String> roles) { return null; }
}
