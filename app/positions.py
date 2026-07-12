"""Position auto-fill logic for AnnoABSA."""
import json
import pandas as pd
from app.config import DATA_FILE_PATH, DATA_FILE_TYPE, AUTO_POSITIONS
from app.data import load_data, save_data


def auto_add_missing_positions():
    """Automatically add missing position data for existing phrases."""
    if not AUTO_POSITIONS:
        print("ℹ️  Auto position filling disabled (use --auto-positions to enable)")
        return

    print("🔍 Scanning for missing position data...")

    try:
        data = load_data()
        data_changed = False
        updated_count = 0

        if DATA_FILE_TYPE == "json":
            # Handle JSON format
            for item in data:
                if 'text' not in item:
                    continue

                text = item['text']
                label_data = item.get('label', [])

                # Handle both string and array formats
                if isinstance(label_data, str):
                    if not label_data or label_data == '':
                        continue
                    try:
                        annotations = json.loads(label_data)
                    except (json.JSONDecodeError, TypeError):
                        continue
                else:
                    # Already an array
                    annotations = label_data

                if not isinstance(annotations, list):
                    continue

                annotations_updated = False

                for annotation in annotations:
                    # Check aspect_term positions
                    if ('aspect_term' in annotation and
                        annotation['aspect_term'] and
                        annotation['aspect_term'] != 'NULL' and
                            ('at_start' not in annotation or 'at_end' not in annotation)):

                        phrase = annotation['aspect_term']
                        start_pos = text.find(phrase)
                        if start_pos != -1:
                            annotation['at_start'] = start_pos
                            annotation['at_end'] = start_pos + len(phrase) - 1
                            annotations_updated = True
                            updated_count += 1

                    # Check opinion_term positions
                    if ('opinion_term' in annotation and
                        annotation['opinion_term'] and
                        annotation['opinion_term'] != 'NULL' and
                            ('ot_start' not in annotation or 'ot_end' not in annotation)):

                        phrase = annotation['opinion_term']
                        start_pos = text.find(phrase)
                        if start_pos != -1:
                            annotation['ot_start'] = start_pos
                            annotation['ot_end'] = start_pos + len(phrase) - 1
                            annotations_updated = True
                            updated_count += 1

                if annotations_updated:
                    # Store as array, not as JSON string
                    item['label'] = annotations
                    data_changed = True

        else:
            # Handle CSV format
            for idx, row in data.iterrows():
                if pd.isna(row.get('text')):
                    continue

                text = row['text']
                label_str = row.get('label', '')

                if not label_str or pd.isna(label_str) or label_str == '':
                    continue

                try:
                    annotations = json.loads(label_str)
                    if not isinstance(annotations, list):
                        continue

                    annotations_updated = False

                    for annotation in annotations:
                        # Check aspect_term positions
                        if ('aspect_term' in annotation and
                            annotation['aspect_term'] and
                            annotation['aspect_term'] != 'NULL' and
                                ('at_start' not in annotation or 'at_end' not in annotation)):

                            phrase = annotation['aspect_term']
                            start_pos = text.find(phrase)
                            if start_pos != -1:
                                annotation['at_start'] = start_pos
                                annotation['at_end'] = start_pos + \
                                    len(phrase) - 1
                                annotations_updated = True
                                updated_count += 1

                        # Check opinion_term positions
                        if ('opinion_term' in annotation and
                            annotation['opinion_term'] and
                            annotation['opinion_term'] != 'NULL' and
                                ('ot_start' not in annotation or 'ot_end' not in annotation)):

                            phrase = annotation['opinion_term']
                            start_pos = text.find(phrase)
                            if start_pos != -1:
                                annotation['ot_start'] = start_pos
                                annotation['ot_end'] = start_pos + \
                                    len(phrase) - 1
                                annotations_updated = True
                                updated_count += 1

                    if annotations_updated:
                        data.at[idx, 'label'] = json.dumps(
                            annotations, ensure_ascii=False)
                        data_changed = True

                except (json.JSONDecodeError, TypeError):
                    continue

        if data_changed:
            save_data(data)
            print(
                f"✅ Auto-added {updated_count} missing position entries and saved to {DATA_FILE_PATH}")
        else:
            print("ℹ️  No missing positions found")

    except Exception as e:
        print(f"❌ Error during auto position filling: {e}")
