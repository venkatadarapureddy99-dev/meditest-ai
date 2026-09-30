package com.meditest.record;

import com.meditest.patient.PatientRepository;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;

@Service
@RequiredArgsConstructor
class RecordService {

    private final RecordRepository records;
    private final PatientRepository patients;

    MedicalRecord add(RecordRequest r) {

        var patient = patients.findById(r.patientId())
                .orElseThrow(() ->
                        new ResponseStatusException(
                                HttpStatus.NOT_FOUND,
                                "patient not found"
                        ));

        var rec = new MedicalRecord();

        rec.setPatient(patient);
        rec.setDiagnosisCode(r.diagnosisCode());
        rec.setNotes(r.notes());

        return records.save(rec);
    }

    List<MedicalRecord> forPatient(Long id) {

        if (!patients.existsById(id)) {
            throw new ResponseStatusException(
                    HttpStatus.NOT_FOUND
            );
        }

        return records.findByPatientId(id);
    }
}

@RestController
@RequiredArgsConstructor
class RecordController {

    private final RecordService service;

    @PostMapping("/api/records")
    @ResponseStatus(HttpStatus.CREATED)
    MedicalRecord add(
            @Valid @RequestBody RecordRequest r) {
        return service.add(r);
    }

    @GetMapping("/api/patients/{id}/records")
    List<MedicalRecord> forPatient(
            @PathVariable Long id) {
        return service.forPatient(id);
    }
}