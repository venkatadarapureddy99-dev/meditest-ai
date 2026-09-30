package com.meditest.appointment;

import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/appointments")
@RequiredArgsConstructor
public class AppointmentController {

    private final AppointmentService service;

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public Appointment book(
            @RequestBody AppointmentRequest r) {
        return service.book(r);
    }

    @GetMapping
    public List<Appointment> list() {
        return service.findAll();
    }
}