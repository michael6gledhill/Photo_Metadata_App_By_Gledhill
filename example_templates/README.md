# Example Templates and Naming Conventions

This directory contains ready-to-use templates and naming conventions that you can import into the Photo Metadata Editor app.

## How to Import

### Method 1: File Import
1. In the app, click the **Import** button under Templates or Naming Conventions
2. Click **Select JSON File...**
3. Choose one of the JSON files from this directory
4. Click **Import**

### Method 2: Copy & Paste
1. Open any JSON file from this directory in a text editor
2. Copy the entire content (Ctrl+A, Ctrl+C)
3. In the app, click the **Import** button
4. Paste the content in the text area (Ctrl+V)
5. Click **Import**

## Metadata Templates

### Portrait Professional (`portrait_professional.json`)
Complete template for professional portrait photography with studio settings and copyright information.

**Includes:**
- Artist and copyright information
- Professional portrait descriptions
- Keywords: portrait, professional, studio, headshot
- Usage rights and credit information

### Travel Photography (`travel_photography.json`)
Template for travel and adventure photography with location fields.

**Includes:**
- Travel-specific keywords
- Location fields (city, state, country)
- Creative Commons licensing option
- Adventure and culture keywords

### Wedding Photography (`wedding_photography.json`)
Comprehensive template for wedding events with client licensing.

**Includes:**
- Wedding-specific fields and keywords
- Venue and location information
- Client usage instructions
- Copyright with client license

### Event Photography (`event_photography.json`)
General event documentation template.

**Includes:**
- Event name and venue fields
- Location information
- Caption writer attribution
- Event keywords

### Stock Photography (`stock_photography.json`)
Optimized for stock photo libraries with extensive keyword support.

**Includes:**
- Multiple keyword fields for searchability
- Royalty-free licensing information
- Genre and category fields
- Web statement link

## Naming Conventions

### Date + Sequence (`date_sequence.json`)
Simple date-based naming with 4-digit sequence numbers.

**Pattern:** `{date}_{sequence:04d}`  
**Example:** `2025-12-08_0001.jpg`

### Timestamp + Camera (`timestamp_camera.json`)
Full timestamp with camera model information.

**Pattern:** `{datetime:%Y%m%d_%H%M%S}_{camera_model}`  
**Example:** `20251208_143052_Canon_EOS_R5.jpg`

### User + Date + Title (`user_date_title.json`)
Includes system username with date and photo title.

**Pattern:** `{userid}_{date}_{title}`  
**Example:** `michael_2025-12-08_sunset.jpg`

### Original + Sequence (`original_sequence.json`)
Preserves original filename with added sequence number.

**Pattern:** `{original_name}_{sequence:03d}`  
**Example:** `IMG_1234_001.jpg`

### Year-Month + Title + Seq (`yearmonth_title_seq.json`)
Groups photos by year and month with title and sequence.

**Pattern:** `{datetime:%Y-%m}_{title}_{sequence:03d}`  
**Example:** `2025-12_portrait_session_001.jpg`

## Customizing Templates

After importing, you can:
1. Select the imported template
2. Click **Edit** to modify fields
3. Update values with your specific information
4. Save your customized version

## Tips

- **Replace placeholders:** Templates with `[Brackets]` are placeholders - edit them with your actual information
- **Keywords:** Add or remove keywords in the arrays to match your content
- **Combine patterns:** Mix and match naming convention tokens for your workflow
- **Test first:** Use Dry Run mode to preview changes before applying

## Available Tokens for Naming Conventions

- `{title}` - Image title/description
- `{date}` - Date in YYYY-MM-DD format
- `{datetime:%FORMAT%}` - Custom datetime format (strftime)
- `{camera_model}` - Camera model from EXIF
- `{sequence:NNd}` - Sequence number with padding
- `{original_name}` - Original filename without extension
- `{userid}` - Current system user

## Need More Examples?

Check the [documentation](https://michael6gledhill.github.io/Photo_Metadata_App_By_Gledhill/) for more examples and usage guides.
