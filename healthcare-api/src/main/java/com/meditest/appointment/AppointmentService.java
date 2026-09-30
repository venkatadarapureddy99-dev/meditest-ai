package com.meditest.appointment;

import com.meditest.patient.PatientRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
@RequiredArgsConstructor
public class AppointmentService {

    private final AppointmentRepository appointments;
    private final PatientRepository patients;

    public Appointment book(AppointmentRequest r) {

        Appointment a = new Appointment();

        // BUG 3: deliberately planted defect
        a.setPatient(
            patients.findById(r.patientId()).get()
        );

        a.setStartsAt(r.startsAt());
        a.setReason(r.reason());

        return appointments.save(a);
    }

    public List<Appointment> findAll() {
        return appointments.findAll();
    }
}