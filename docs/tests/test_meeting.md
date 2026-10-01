# `tests/test_meeting.py`

47 tests. Source: [`tests/test_meeting.py`](../../tests/test_meeting.py).


## TestReadWav

- `test_round_trip`: round trip
- `test_rejects_stereo`: rejects stereo

## TestTranscribeChunk

- `test_sends_text_and_deletes_the_chunk`: sends text and deletes the chunk
- `test_them_chunks_get_speaker_numbers`: them chunks get speaker numbers
- `test_bad_file_still_reports_and_never_raises`: bad file still reports and never raises

## TestSplitAtSpeakerChanges

One chunk with two people in it comes back as two lines, one per person.

- `test_two_people_two_lines_at_their_times`: two people two lines at their times
- `test_same_person_segments_are_joined`: same person segments are joined
- `test_a_short_word_joins_the_speaker_before_it`: a short word joins the speaker before it
- `test_all_short_segments_use_the_whole_chunk`: all short segments use the whole chunk
- `test_nothing_said_still_reports_once`: nothing said still reports once

## TestEmbeddingClusters

Diarization rules with voice fingerprints: join >= 0.40, a new person only after a second

- `test_joins_the_closest_person`: joins the closest person
- `test_one_odd_sentence_never_makes_a_new_person`: one odd sentence never makes a new person
- `test_people_who_turn_out_alike_are_merged_and_reported`: people who turn out alike are merged and reported
- `test_short_unclear_speech_never_starts_a_new_person`: short unclear speech never starts a new person
- `test_only_clear_speech_refines_a_voice`: only clear speech refines a voice
- `test_too_short_to_fingerprint_is_the_last_speaker`: too short to fingerprint is the last speaker
- `test_at_most_eight_people`: at most eight people
- `test_falls_back_to_the_signature_without_a_model`: falls back to the signature without a model
- `test_merges_are_sent_to_the_app`: merges are sent to the app

## TestGender

Male/female: fingerprint classifier averaged with pitch.

- `test_shipped_weights_load_for_titanet`: shipped weights load for titanet
- `test_missing_or_mismatched_is_none`: missing or mismatched is none
- `test_fingerprint_and_pitch_are_averaged`: fingerprint and pitch are averaged
- `test_classifier_output_is_a_probability`: classifier output is a probability

## TestSpeakerEmbedder

- `test_unavailable_model_means_none_once`: unavailable model means none once
- `test_uses_sherpa_onnx_and_returns_a_unit_vector`: uses sherpa onnx and returns a unit vector
- `test_zero_vector_is_none`: zero vector is none

## TestVoiceClusters

- `test_same_voice_same_speaker`: same voice same speaker
- `test_different_voices_after_a_second_sentence`: different voices after a second sentence
- `test_too_short_to_measure_joins_the_main_speaker`: too short to measure joins the main speaker

## TestSummary

- `test_parses_the_model_json`: parses the model json
- `test_unparseable_reply_is_none`: unparseable reply is none
- `test_empty_meeting_skips_the_model`: empty meeting skips the model
- `test_transcript_text`: transcript text

## TestAsk

- `test_answers`: answers
- `test_what_did_i_miss_is_an_empty_question`: what did i miss is an empty question
- `test_nothing_said_yet`: nothing said yet

## TestPushedLevels

- `test_push_then_decay`: push then decay
- `test_clamped`: clamped

## TestVoiceKind

- `test_pitch_of_a_low_and_a_high_voice`: pitch of a low and a high voice
- `test_noise_has_no_pitch`: noise has no pitch
- `test_male_female_by_pitch_around_145_hz`: male female by pitch around 145 hz
- `test_reported_with_each_chunk`: reported with each chunk

## TestPreviewThread

Live previews run on their own thread with the small model, so final text never waits.

- `test_two_threads_and_previews_use_the_small_model`: two threads and previews use the small model
- `test_without_a_small_model_previews_share_the_queue`: without a small model previews share the queue

## TestPreview

- `test_preview_is_marked_partial_and_skips_speakers`: preview is marked partial and skips speakers
- `test_only_the_newest_preview_runs`: only the newest preview runs
- `test_streams_preview_independently`: streams preview independently
