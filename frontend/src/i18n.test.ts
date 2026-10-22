import { describe, expect, it } from 'vitest';
import { apiErrorMessage, codeLabel, dateLabel, fileAnalysisLabel, fileClassLabel, healthLabel, languageLabel, snapshotStatusLabel, translateText } from './i18n';
import { ApiError } from './api/client';

describe('Turkish analyzer contract', () => {
  it.each([
    ['partial', 'Kısmi'], ['completed', 'Tamamlandı'], ['unavailable', 'Kullanılamıyor'],
    ['cycles', 'Bağımlılık döngüleri'], ['test_presence', 'Test dosyası eşleşmesi'],
    ['large_function', 'Uzun fonksiyon'], ['large_class', 'Büyük sınıf'], ['many_members', 'Çok sayıda metot'], ['high_fan_in', 'Çok sayıda kullanan dosya'], ['high_fan_out', 'Çok sayıda bağımlılık'], ['mutual_dependency', 'Karşılıklı bağımlılık'],
    ['warning', 'Uyarı'], ['notice', 'Bilgi'], ['high', 'Yüksek'], ['medium', 'Orta'], ['low', 'Düşük'], ['none', 'Yok'],
    ['estimated', 'Tahmin edildi'], ['insufficient_evidence', 'Yetersiz kanıt'], ['no_snapshot', 'Analiz yok'],
    ['met', 'Karşılandı'], ['unmet', 'Karşılanmadı'], ['unknown', 'Bilinmiyor'],
    ['done_but_unmet', 'Tamamlandı işaretli, ölçütler eksik'], ['evidence_complete_but_not_done', 'Kanıtlar tamam, görev açık'],
    ['file_exists', 'Dosya varlığı'], ['path_has_files', 'Klasörde dosya varlığı'], ['import_edge_exists', 'İçe aktarım bağlantısı'], ['not_in_cycle', 'Döngüde yer almama'], ['max_todo_markers', 'TODO/FIXME üst sınırı'], ['no_analysis_failures', 'Analiz hatası olmaması'], ['manual_attestation', 'Elle doğrulama'],
    ['manifest', 'Bildirim dosyası'], ['framework', 'Çatı'], ['test framework', 'Test çatısı'], ['state management', 'Durum yönetimi'],
    ['name', 'Ad eşleşmesi'], ['import', 'İçe aktarım eşleşmesi'], ['(uncategorized)', 'Kategorisiz'], ['(no section)', 'Bölümsüz'],
  ])('translates stable code %s', (value, expected) => expect(codeLabel(value)).toBe(expected));

  it('covers actual scanner and snapshot states, including diagnostic analysis', () => {
    expect(fileClassLabel('dart_source')).toBe('Dart kaynak kodu');
    expect(fileClassLabel('other')).toBe('Diğer');
    for (const state of ['scanned', 'analyzed', 'analyzed_with_diagnostics', 'parse_failed', 'unreadable', 'skipped_size_limit']) expect(fileAnalysisLabel(state)).not.toBe(state);
    for (const state of ['queued', 'running', 'succeeded', 'failed', 'complete', 'partial']) expect(snapshotStatusLabel(state)).not.toBe(state);
    expect(healthLabel('attention')).toBe('İlgi gerekiyor');
    expect(languageLabel('python')).toBe('Python');
    expect(languageLabel('dart')).toBe('Dart');
    expect(dateLabel(null)).toBe('Tarih bilinmiyor');
    expect(dateLabel('2026-10-22T12:00:00Z')).toMatch(/22 Eki 2026/);
  });

  it.each([
    ['3 of 12 graph files are in cycles (0.250); 25% saturates the penalty.', '12 grafik dosyasının 3 tanesi döngüde'],
    ['2 of 8 local or unresolved import references are unresolved (0.250); external imports are excluded.', 'harici içe aktarımlar hariçtir'],
    ['4 of 5 source files have a matching test file by name/import heuristic, not coverage (0.800).', 'bu, test kapsamı değildir'],
    ['8 TODO/FIXME markers across 2000 physical LOC (4.0 per KLOC); 20 per KLOC saturates the penalty.', '1.000 LOC başına 4.0'],
    ['Marker data is incomplete (2 files unavailable), with 8 known markers across 2000 LOC; TODO/FIXME density cannot be scored.', '2 dosyada işaret verisi eksik'],
    ['Known physical LOC is 0 and marker count is 2; zero LOC prevents a density score.', 'sıfır LOC nedeniyle yoğunluk puanlanamıyor'],
    ['Weighted mean of 3 available components; weights renormalized to 0.80.', '3 kullanılabilir bileşenin ağırlıklı ortalaması'],
    ['Only 1 of 4 components are available; at least 2 are required for an overall score.', 'genel puan için en az 2 bileşen gerekir'],
    ['12 commits in the history window', 'Geçmiş aralığında 12 commit'], ['1200 physical LOC', '1200 fiziksel LOC'],
    ['file is in 2 dependency cycle group(s)', '2 bağımlılık döngüsü'], ['11 incoming local dependency edges', '11 gelen yerel bağımlılık'],
    ['Function spans 160 lines; threshold is 80 lines.', 'Fonksiyon 160 satır'],
    ['Class-like declaration spans 450 lines; threshold is 400 lines.', 'Sınıf benzeri bildirim 450 satır'],
    ['Class-like declaration has 32 direct methods; threshold is 30 methods.', '32 doğrudan metot'],
    ['File has 17 distinct local dependencies; threshold is 15.', '17 farklı yerel bağımlılığı'],
    ['File has 11 distinct local dependents; threshold is 10; it is a central dependency where changes have wide impact, not necessarily a defect.', 'mutlaka bir hata değildir'],
    ['file exists but is not fully analyzed (parse_failed)', 'Ayrıştırılamadı'],
    ['file analysis status is not recognized (future_state)', 'future_state'],
    ['found 3 fully analyzed matching files (minimum 2)', 'en az 2'],
    ['found 1 fully analyzed matching files; minimum is 2 and snapshot is partial', 'analiz kısmi'],
    ['known marker total 7 exceeds maximum 5; more markers may exist', 'daha fazla işaret olabilir'],
    ['known marker total 3 is within maximum 5, but coverage is incomplete', 'inceleme eksik'],
    ['marker total 2 is at most 3', '3 üst sınırını aşmıyor'],
    ['Estimate uses 1 met and 1 unmet automatic criteria; 2 unknown criteria are excluded from the percentage.', 'belirsiz 2 ölçüt yüzdeye katılmadı'],
    ['Confidence is medium because the snapshot is partial.', 'Orta; analiz kısmi olduğu için düşürüldü'],
    ['All 3 automatic criteria are unknown.', '3 otomatik ölçütün tamamı belirsiz'],
    ['src/a.py: TODO/FIXME data incomplete', 'src/a.py: TODO/FIXME verisi eksik'], ['known total: 8', 'Bilinen toplam: 8'],
    ['invalid_criterion: absolute paths are not allowed', 'Geçersiz ölçüt: Mutlak yollara izin verilmez'],
    ['invalid_criterion: unexpected params [\'x\']; missing params [\'path\']', 'Beklenmeyen parametreler'],
    ['512 bytes exceeds limit of 256', '512 bayt, 256 bayt sınırını aşıyor'],
    ['unterminated block comment (line 7)', 'Kapatılmamış blok yorumu (satır 7)'], ['invalid syntax (line 2)', 'Geçersiz sözdizimi (satır 2)'],
    ["package name 'app' is declared by multiple pubspec.yaml files", "'app' paket adı"],
    ["relative URI '../outside.dart' escapes the repository root", 'depo kökünün dışına çıkıyor'],
    ['ParserError: invalid syntax', 'Ayrıştırıcı hatası: Geçersiz sözdizimi'],
  ])('translates backend sentence: %s', (input, expected) => expect(translateText(input)).toContain(expected));

  it.each([
    'No eligible Python/Dart graph files are available (0 denominator).', 'No local or unresolved import references are available (0 denominator).',
    'No source files are available for test file presence by name/import heuristic, not coverage (0 denominator).',
    'manual attestation is user-reported, not automatic evidence', 'file is absent from a partial snapshot', 'file is absent from the snapshot', 'file is present and analyzed',
    'local import edge is present', 'source or target file is absent or not fully analyzed', 'edge is absent from a partial snapshot', 'local import edge is absent',
    'file belongs to a dependency cycle', 'file is not fully analyzed in a partial snapshot', 'file is not in a reported dependency cycle', 'no files are covered by this path',
    'one or more covered files have analysis failures', 'no covered files have a known analysis failure', 'no analysis snapshot is available',
    'No analysis snapshot is available; progress cannot be estimated.', 'No automatic criteria produced met or unmet evidence, so no percentage is estimated.',
    'Linked files provide context only; their existence is not completion evidence.', 'Manual attestations are reported separately and do not affect the estimate.',
    'Manual status is DONE while automatic evidence estimates less than 100% completion.', 'Automatic evidence estimates 100% with medium or high confidence while manual status is not DONE.',
    'Completed percentage is DONE tasks divided by all tasks; IN_PROGRESS earns no partial credit, and BLOCKED tasks remain in the denominator. Empty roadmaps have no percentage.',
    'analysis output path excluded', 'symlink was not followed or read', 'directory excluded by scanner rules', 'file excluded by scanner rules', 'virtual environment detected by pyvenv.cfg', 'ProjectLens result JSON excluded',
    'pubspec.yaml has no valid top-level name', 'shallow_history', 'Permission denied',
    'heuristic indicator from static analysis; not a measure of correctness or coverage', 'explainable heuristic; not a prediction of defects',
    'Generated by AI from bounded ProjectLens analysis context; verify cited sources.',
  ])('covers exact fixed backend phrase: %s', input => expect(translateText(input)).not.toBe(input));

  it('prefers API error codes and preserves truly unknown server messages', () => {
    expect(new ApiError(404, 'project_not_found', 'Project was not found.').message).toBe('Proje bulunamadı.');
    expect(apiErrorMessage('project_analysis_active', 'English')).toContain('proje silinemez');
    for (const code of ['snapshot_not_found', 'job_not_found', 'task_not_found', 'validation_error', 'internal_error', 'queue_full', 'checkout_timeout', 'checkout_failed', 'invalid_ref', 'analysis_failed', 'worker_unavailable', 'project_missing', 'invalid_status_transition', 'duplicate_link', 'link_limit_reached', 'criteria_limit_reached', 'request_too_large', 'assessment_task_limit', 'roadmap_import_conflict', 'invalid_checklist', 'link_not_found', 'criterion_not_found', 'task_item_not_found']) expect(apiErrorMessage(code, 'English')).not.toBe('English');
    expect(apiErrorMessage('future_code', 'Custom server message')).toBe('Custom server message');
    expect(translateText('A new analyzer explanation')).toBe('A new analyzer explanation');
    expect(codeLabel('future_enum')).toBe('future_enum');
    expect(translateText('src/partial.py')).toBe('src/partial.py');
  });
});
