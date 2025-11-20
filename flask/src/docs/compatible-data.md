# CRAB Compatible Data

CRAB accepts arbitrary data as parquet files.

> [!NOTE]
> This format is still a living standard, and is not considered final. Feedback is greatly appreciated.

## Goals and justification

The main goals for this specification are to be:

0. Optimised for scientific data.
1. Search optimised, even without an index.
2. Suitable for fedaration, with no central authority.
3. Auditable, with full change tracking.
4. Partition tolerant, and repairable.

0 - Scientific data comes in all shapes and sizes, so CRAB is designed to accept data in all shapes and sizes. The goal is simple; anything that can be represented as an array can be stored, indexed and annotated in CRAB.

1 - Being search optimised on-disk is important, as a system that has limited local disk space, but virtually unlimited object store space hugely benefits from the ability to keep as small an internal database as possible. This is key to addressing concerns of managing large volumes of data with limited raw disk space, as is often the case in research organisations.

2 - Unique, but detrministic identifiers [UDTs](https://github.com/NOC-OI/universal-data-tracker-spec/blob/main/main.pdf) are heavily relied upon to ensure data can be shared, indexed and collaborated upon in both public and private, with the ability to integrate data from different research organisations. 

3 - Having a full audit log is vital for maintaining scientific integrigty, and is thus a core part of the design. Inherent to the design is an ability to not only search the current accepted data, but also revision history and disputed entries.

4 - Partition tolerance is of particular importance to marine science, where there is often unreliable network connections with a single point of failure. Outside of the specific case of network partition, it is often useful to preserve annotations even if the underlying raw data is lost. The system must fail gracefully, with just enough information to still recover instrument information and original data collection times.

## Data files

Raw orthogonal data, and metadata from the original instrument.

### Per-file metadata

| Key | Expected value |
| --- | --- |
| data_type | Literal string "CRAB_DATA_V1" |
| last_modified | uint64, Unix timestamp of last modification |
| contains_udts | Concatenated binary string of binary UDTs |

**Example for a RGB microscopic image system:**

| Key | Value |
| --- | --- |
| data_type | CRAB_DATA_V1 |
| last_modified | 1762184335 |
| contains_udts | 0x022dc621accf3dc224a43f022373c200006839044c |

### Per-entry values

| Key | Expected value |
| --- | --- |
| udt | Full UDT |
| udt_bin | Binary compact UDT, for search |
| data | Raw binary data |
| data_uri | String, should be a publicly accessible URI for the data. MAY be null if data is present in-file. May be provided in addition to data in-file. |
| sha256 | Binary, SHA256 hash of the data (should match the output of sha256sum on the raw binary data) |
| mime_type | String mime type for data, see note below for handling of mime types |
| numerical_format | String, represents the format of values in the resulting data. See note below about numerical format. |
| domain_types | JSON encoded array, stating the type of each domain. See note below about domain types. |
| bit_depth | uint64, the original bit depth of the data, regardless of current numerical format. E.g. a 12-bit camera image stored in a 16-bit image format would have the value 12 here. |
| last_modified | uint64, Unix timestamp of data collection |
| extents | Array of uint64, one for each dimension |

**Example for an IFCB greyscale plankton imaging system:**

| Key | Value |
| --- | --- |
| udt | udt1__usa_mc_lane_research_laboratories__imaging_flow_cytobot__225__1748567116__19 |
| udt_bin | 0x032dc621accf3dc224a43f022373c200006839044c9400f1b21cb527d7 |
| data | <raw_array_data\> |
| data_uri | null |
| sha256 | 0xf22136124cd3e1d65a48487cecf310771b2fd1e83dc032e3d19724160ac0ff71 |
| mime_type | application/octet-stream |
| numerical_format | uint8 |
| domain_types | \["spatial 3.5714285714285716e-07 m", "spatial 3.5714285714285716e-07 m", "chromatic 1.5e-07 m"\] |
| bit_depth | 8 |
| last_modified | 1762184646 |
| extents | 400, 600 |

#### Note regarding use_dictionary
It is highly reccomended to use the "use_dictionary" parameter for "domain_types", "mime_type" and "numerical_format".

#### Handling of mime types
The default application/octet-stream will be interpreted as a NumPy array in C (column major) order. Using extents and the numerical_format, an arbitrary NumPy array can be reconstructed. This data type is the preferred default, with other formats only being used when neccesary for compression (e.g. video). Especially for collections of small images (<200px wide/high), the NumPy array type should be used over image formats, as image format overheads will usually outweigh any space savings from image-specific compression.

Other popular container formats supported include:

- video/matroska* (only video stream supported)
- video/mp4
- audio/matroska*
- audio/flac
- audio/wav
- audio/mpeg
- image/jpeg
- image/jp2
- image/png
- image/tiff

*Codecs supported include:

- H.264
- H.265
- FLAC
- AAC
- MP3
- Vorbis
- Ogg

Just because your codec isn't listed here, doesn't mean CRAB will not support it, but these should be used for maximum compatibility.

#### Numerical format
For compatibility, this must be a power of two NumPy numerical type (i.e. float64 and float128 is permitted, but not float96). Any data in a crab compatible data container must be coercible to a NumPy array. This holds true for the vast majority of multimedia containers that could be used. For example, a 30fps ROV dive video in the H.264 codec in an Matroska container could be translated into a rather unweildly 4D array of unit8, with the domain types \["temporal 0.03333333333333333 s", "angular", "angular", "chromatic 1.5e-07 m"\]. This would likely not be done in practice, but is neccesary functionality to allow true interoperability with arbitrary N-dimensional processing.

#### Note about domain types

Usual domain types are: "spatial", "angular", "chromatic", "temporal", "frequency", "feature". Each domain type definition should state the scale of each dimension, and an SI unit symbol as a suffix. The SI unit symbol should be without prefix, and separated from the number with a space. 

The number should represent the minimum distance between any two points for a given dimension. For example, a microscope might have a digital resolution of 2.8 pixels per um, which should be represented as "3.5714285714285716e-07 m". This represents the minimum distance resolveable (assuming perfect optics) and can be used to calculate object sizes.

Cameras (with few exceptions) capture perspective images, and an exact spatial relationship cannot be drawn. For this case, the angular domain type is useful, where we can make a definitive judgement about field of view. A camera with a sensor size of 600x400 pixels and a horizontal FOV of 60 degrees could be represented as "angular 0.0017453292519943294 rad". This models each pixel as having a covered area of 0.0017453292519943294 radians.

Where the distances point to point vary inconsistently (e.g. in a Chroma dimension for frequency, or a spatial dimension for line-scan camera data), an average may be used. In cases where a resolution is not applicable (e.g. in feature space), the dimension suffix may be omitted. In this case the entire string would be "feature" with no trailing spaces. In the case where a dimension steps in a non-linear way, an additional suffix of "log <base\>" should be used, with the first gap being given as the resolution. For example, a spectrogram with the following frequency bins; 4Hz, 8Hz, 16Hz, 32Hz; should use the domain type: "frequency 4 Hz log 2". Fractional log bases are allowed for inverse logarithmic scaling.

While it may seem abstract, each domain type has a specific function to allow definition of arbitrary orthagonal data:

- Spatial dimensions might be the most obvious type. Each different spatial dimention represents a new spatial axis that a data point might refer to.

- Temporal dimensions are another common type, that is largely self explanatory. It generally only makes sense to have one such dimension, and many annotation suites will be unable to process any more than the first temporal dimension.

- A feature dimension is a dimension which represents a change in type of data. One example for use of such data might be in water monitoring, for separating the different features of salinity, temperature and turbidity. In this case there would be a "feature" dimension of extent 3.

- Chromatic and frequency dimensions are a special case of feature dimensions, and CRAB will treat them identically in data processing, but differently for display purposes. They are used for colour channels in images and frequency bins in spectrogram data respectively. Both chromatic and frequency dimensions should increase starting from 0. In practice this means the standard RGB pattern should be used. In non-RGB cameras, care should be taken to put lower frequency (higher wavelength) information before higher frequency (lower wavelength) information, for example, infrared would come before red green and blue. Cameras that output YCrCb or similar signals should be translated to RGB. For Chroma specifically, wavelength is preferred as a unit over frequency for the sake of standardisation. 

#### Note about domain order

Domains should be ordered from most commonly separated to least commonly separated. This is because of the column-major array order. Logically, dimensions that are commonly sliced along, such as time, should go first in a column-major format, as this allows individual time-steps to be read as a smaller chunk of disk access. This has large implications for the efficiency of data processing, as if a seperable dimension is places later in the order, disk reads become discontinuous when selecting part of an array. Moderns processors also work more effectively on condiguous data, so it is important to ensure that contiguous segments can be read most of the time. For video data, an example layout might be:

- Time (temporal)
- Pixel Y (spatial)
- Pixel X (spatial)
- RGB (chroma)

Since we very rarely split video into R, G and B channels, it makes sense that that should be the least efficient operation. Time being the most common way to split a video (e.g. taking a single frame from a video), therefore becomes the most efficient operation. If you did however regularly finding yourself splitting R, G and B channels, you might consider a domain layout as such:

- Time (temporal)
- RGB (chroma)
- Pixel Y (spatial)
- Pixel X (spatial)

This would make RGB splits the second most efficient operation. It is important to note that compatible software should be able to decode the data no matter the order, and this is simply a matter of performance. Choosing one order over another affects speed, not what is possible to do with the data.

On a side note, it is also sometimes useful to adopt the order or popular tools. Pixel Y comes before Pixel X here as this is the order that OpenCV will expect dimensions to be in. Therefore for image data, CRAB reccomends placing Y first and X second to avoid unexpectedly rotated imaged.

## Annotation files

Each annotation is attached to a specific extent, of a specific data frame. In a biological context, the most important metadata tag is usually "taxa", which should contain taxanomic information relative to the chosen authoratative taxonomy. Other metadata might be stored in an annotation however, such as particle size or other morphological measurements. Annotations are broken up into individual entries, where each one represents a log of changes. This provides a mechanism for inherent change tracking, and maintains searchability of disputed entries.

### Per-file metadata

| Key | Expected value |
| --- | --- |
| data_type | Literal string "CRAB_ANNOTATION_V1" |
| last_modified | uint64, Unix timestamp of last modification |
| references_udts | Concatenated binary string of binary compact UDTs referenced |
| x_<metadata_name\> | **(optional)** Arbitrary fields for use in application-specific scenarios |

#### Example for annotations from EcoTaxa**

| Key | Value |
| --- | --- |
| data_type | CRAB_ANNOTATION_V1 |
| last_modified | 1762184646 |
| references_udts | 0x022dc621accf3dc224a43f022373c200006839044c |

### Per-entry values

| Key | Expected value |
| --- | --- |
| udt | Full UDT |
| udt_bin | Binary compact UDT, for search |
| uuid | In compact binary form, used as the unique identifier for this annotation |
| sha256 | Binary, SHA256 hash of the exact data source the annotation was originally generated for |
| last_modified | uint64, Unix timestamp of annotation modification time |
| extents | Array of uint64, **two** for each dimension, first an lower bound, then an upper bound |
| origin_extents | Array of uint64, **one** for each dimension, gives the maximum dimension size of the original data as created. See note below. |
| annotator | String, an email address or ORCID identifier (MUST be formatted with dashes). MUST be null if no human involvement |
| annotation_software | String, URI reference to the software used to create the annotation, preferably the source code repository |
| discard_in_favour | **(optional)** Usually null or empty. Used to replace or update the extents of an annotation. |
| field_<field_name\> | **(optional, but reccomended)** Arbitrary fields for use in annotation, common ones listed below. Null values will be ignored, *and will not overwrite existing values* |
| discard_field_<field_name\> | **(optional)** Boolean, special mark to indicate that the field should be discarded, as if it were deleted. Should be true on deleted fields, false or null otherwise. |

#### Example for ROI only information from IFCBProc

| Key | Value |
| --- | --- |
| udt | udt1__usa_mc_lane_research_laboratories__imaging_flow_cytobot__225__1748567116__19 |
| udt_bin | 0x032dc621accf3dc224a43f022373c200006839044c9400f1b21cb527d7 |
| uuid | 0x486b38eefc0a4a1aa16a1ac3b0eb5ed8 |
| sha256 | 0xf22136124cd3e1d65a48487cecf310771b2fd1e83dc032e3d19724160ac0ff71 |
| last_modified | 1762184586 |
| extents | 0, 400, 0, 600 |
| origin_extents | 400, 600 |
| annotator | null |
| annotation_software | https://github.com/NOC-OI/ifcbproc |

#### Example for annotations from EcoTaxa

| Key | Value |
| --- | --- |
| udt | udt1__usa_mc_lane_research_laboratories__imaging_flow_cytobot__225__1748567116__19 |
| udt_bin | 0x032dc621accf3dc224a43f022373c200006839044c9400f1b21cb527d7 |
| uuid | 0x486b38eefc0a4a1aa16a1ac3b0eb5ed8 |
| sha256 | 0xf22136124cd3e1d65a48487cecf310771b2fd1e83dc032e3d19724160ac0ff71 |
| last_modified | 1762184586 |
| extents | 0, 400, 0, 600 |
| origin_extents | 400, 600 |
| annotator | alewin@noc.ac.uk |
| annotation_software | https://github.com/ecotaxa/ecotaxa |
| field_taxon | https://www.gbif.org/species/8211946 |

#### Common fields

- taxon (e.g. https://www.gbif.org/species/8211946, or urn:lsid:marinespecies.org:taxname:149093)
- major_axis_um (e.g. 129)

When creating fields, it is always advisable to use URIs wherever possible. URIs are preferred as they are instantly recognisable, and allow new users to easily access further information. Parquet's dictionary compresson means that the excess size of URIs is not a problem for search or storage, so long as single, authorotative sources are used.

For taxonomic data, CRAB reccomends using GBIF URIs to refer to species. While a WoRMS LSID is a suitable alternative (and will be recognised by CRAB), a GBIF URI is more immediately usable when encountered in the wild, and is preferred for datasets intended for public distribution.

#### Note regarding discard_in_favour
Discard in favour is used as a special annotation type that tells the system that all previous annotations regarding the region of interest bounded by the extents should be moved to the location specified in the new annotation. The new annotation is referred to by its binary-form UUID. When this value is null, this field is ignored. In order to totally delete a region of interest, this value should be set to the null UUID (00000000-0000-0000-0000-000000000000). This mechanism preserves change tracking when the extents are changed.

#### Note regarding origin_extents
Origin extents address the case where there are multiple copies of the original data that have undergone different post processing. One example would be a video that has been compressed to a lower resolution, and has multiple different resolutions as seperate entries in the database. It is therefore useful to know how to scale annotations where multiple sources exist.

#### Note regarding use_dictionary
It is highly reccomended to use the "use_dictionary" parameter for "annotator", "annotation_software" and any other string field with high repitition. For biological data this usually includes fields such as "taxon" where there are a lot of duplicated string entries. With a lot of fields, it might make sense to increase the max dictionary size. Anaecdotally, around 2MB results in good performance on S3 backed storage, but decreased row group sizes of 32-64MB are needed for lower memory use.

