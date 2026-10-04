package com.meditest.patient;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import java.util.*;

@Service
@RequiredArgsConstructor
public class PatientService {

    private final PatientRepository repo;

    public Patient create(Patient p) {
    if (p.getBloodType() != null) {
        p.setBloodType(p.getBloodType().trim().toUpperCase());
    }
    return repo.save(p);
}


    public Optional<Patient> find(Long id) {
        return repo.findById(id);
    }

    public List<Patient> findAll() {
        return repo.findAll();
    }
}