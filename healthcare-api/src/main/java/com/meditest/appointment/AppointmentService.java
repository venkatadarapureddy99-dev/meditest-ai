package com.meditest.appointment;

import com.meditest.patient.Patient;
import com.meditest.patient.PatientRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;

@Service
@RequiredArgsConstructor
public class AppointmentService {

    private final AppointmentRepository appointments;
    private final PatientRepository patients;

    public Appointment book(AppointmentRequest r) {

        Appointment a = new Appointment();

        Patient patient = patients.findById(r.patientId())
                .orElseThrow(() ->
                        new ResponseStatusException(
                                HttpStatus.NOT_FOUND,
                                "Patient not found"
                        ));

        a.setPatient(patient);
        a.setStartsAt(r.startsAt());
        a.setReason(r.reason());

        return appointments.save(a);
    }

    public List<Appointment> findAll() {
        return appointments.findAll();
    }
}