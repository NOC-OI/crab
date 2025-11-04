# CRAB Compatible Data

CRAB accepts arbitrary data as parquet files.

## Data files

Raw orthogonal data, and metadata from the original instrument.

### Per-file metadata

| Key | Expected value |
| --- | --- |
| data_type | Literal string "CRAB_DATA_V1" |
| last_modified | uint64, Unix timestamp of last modification |
| domain_types | JSON encoded array, stating the type of each domain. See note below about domain types. |
| bit_depth | uint64, the bit depth of the data |
| stored_bit_depth | uint64, how many bits per value. This MAY be different from bit_depth, for example 7-bit ADC data MAY be stored as the least significant of 8-bits to allow for byte-aligned arrays. |
| contains_udts | Concatenated binary string of binary UDTs |

**Example for a RGB microscopic image system:**

| Key | Value |
| --- | --- |
| data_type | CRAB_DATA_V1 |
| last_modified | 1762184335 |
| domain_types | \["spatial 3.5714285714285716e-07 m", "spatial 3.5714285714285716e-07 m", "chromatic 1.5e-07 m"\] |
| bit_depth | 8 |
| stored_bit_depth | 8 |
| contains_udts | 0x022dc621accf3dc224a43f022373c200006839044c |

#### Note about domain types

Usual domain types are: "spatial", "chromatic", "temporal", "frequency", "feature". Each domain type definition should state the scale of each dimension, and an SI unit symbol as a suffix. The SI unit symbol should be without prefix, and separated from the number with a space. 

The number should represent the minimum distance between any two points for a given dimension. For example, a microscope might have a digital resolution of 2.8 pixels per um, which should be represented as "3.5714285714285716e-07 m". This represents the minimum distance resolveable (assuming perfect optics) and can be used to calculate object sizes.

Where the distances point to point vary inconsistently (e.g. in a Chroma dimension for frequency, or a spatial dimension for line-scan camera data), an average may be used. In cases where a resolution is not applicable (e.g. in feature space), the dimension suffix may be omitted. In this case the entire string would be "feature" with no trailing spaces. In the case where a dimension steps in a non-linear way, an additional suffix of "log <base\>" should be used, with the first gap being given as the resolution. For example, a spectrogram with the following frequency bins; 4Hz, 8Hz, 16Hz, 32Hz; should use the domain type: "frequency 4 Hz log 2". Fractional log bases are allowed for inverse logarithmic scaling.

While it may seem abstract, each domain type has a specific function to allow definition of arbitrary orthagonal data:

- Spatial dimensions might be the most obvious type. Each different spatial dimention represents a new spatial axis that a data point might refer to.

- Temporal dimensions are another common type, that is largely self explanatory. It generally only makes sense to have one such dimension, and many annotation suites will be unable to process any more than the first temporal dimension.

- A feature dimension is a dimension which represents a change in type of data. One example for use of such data might be in water monitoring, for separating the different features of salinity, temperature and turbidity. In this case there would be a "feature" dimension of extent 3.

- Chromatic and frequency dimensions are a special case of feature dimensions, and CRAB will treat them identically in data processing, but differently for display purposes. They are used for colour channels in images and frequency bins in spectrogram data respectively. Both chromatic and frequency dimensions should increase starting from 0. In practice this means the standard RGB pattern should be used. In non-RGB cameras, care should be taken to put lower frequency (higher wavelength) information before higher frequency (lower wavelength) information, for example, infrared would come before red green and blue. Cameras that output YCrCb or similar signals should be translated to RGB. For Chroma specifically, wavelength is preferred as a unit over frequency for the sake of standardisation. 

#### Note about domain order

Domains should be ordered from most commonly separated to least commonly separated. This is because of the column-major array order. Logically, dimensions that are commonly sliced along, such as time, should go first in a column-major format, as this allows individual time-steps to be read as a smaller chunk of disk access. This has large implications for the efficiency of data processing, as if a seperable dimension is places later in the order, disk reads become discontinuous when selecting part of an array. Moderns processors also work more effectively on condiguous data, so it is important to ensure that contiguous segments can be read most of the time. For video data, an example layout might be:

- Time (temporal)
- Pixel X (spatial)
- Pixel Y (spatial)
- RGB (chroma)

Since we very rarely split video into R, G and B channels, it makes sense that that should be the least efficient operation. Time being the most common way to split a video (e.g. taking a single frame from a video), therefore becomes the most efficient operation. If you did however regularly finding yourself splitting R, G and B channels, you might consider a domain layout as such:

- Time (temporal)
- RGB (chroma)
- Pixel X (spatial)
- Pixel Y (spatial)

This would make RGB splits the second most efficient operation. It is important to note that compatible software should be able to decode the data no matter the order, and this is simply a matter of performance. Choosing one order over another affects speed, not what is possible to do with the data.

### Per-entry values

| Key | Expected value |
| --- | --- |
| udt | Full UDT |
| udt_bin | Binary compact UDT, for search |
| data | Raw binary data, column major |
| last_modified | uint64, Unix timestamp of data collection |
| extents | Array of uint64, one for each dimension |

**Example for an IFCB greyscale plankton imaging system:**

| Key | Value |
| --- | --- |
| udt | udt1__usa_mc_lane_research_laboratories__imaging_flow_cytobot__225__1748567116__19 |
| udt_bin | 0x032dc621accf3dc224a43f022373c200006839044c9400f1b21cb527d7 |
| data | <raw_array_data\> |
| last_modified | 1762184646 |
| extents | 400, 600 |

## Region of interest

Each ROI simply maps out the extents of an observation. This is often an automatic process, and may be abstracted into higher dimensions. Each ROI has a UUID assigned to ensure change tracking can be carried out effectively. A ROI might be seen as a type of annotation, but it is often useful to seperate it from the process of identification and classification.

### Per-file metadata

| Key | Expected value |
| --- | --- |
| data_type | Literal string "CRAB_ROI_V1" |
| last_modified | uint64, Unix timestamp of last modification |
| references_udts | Concatenated binary string of binary compact UDTs referenced |
| x_<metadata_name\> | **(optional)** Arbitrary fields for use in application-specific scenarios |

**Example for annotations from IFCBProc**

| Key | Value |
| --- | --- |
| data_type | CRAB_ROI_V1 |
| last_modified | 1762184646 |
| references_udts | 0x022dc621accf3dc224a43f022373c200006839044c |

### Per-entry values

| Key | Expected value |
| --- | --- |
| udt | Full UDT |
| udt_bin | Binary compact UDT, for search |
| uuid | In compact binary form, used as the unique identifier of the ROI |
| last_modified | uint64, Unix timestamp of ROI modification time |
| extents | Array of uint64, **two** for each dimension, first an lower bound, then an upper bound |
| annotator | String, an email address or ORCID identifier (MUST be formatted with dashes). MUST be null if no human involvement |
| annotation_software | String, URI reference to the software used to create the ROI, preferably the source code repository |
| x_<metadata_name\> | **(optional)** Arbitrary fields for use in application-specific scenarios |

**Note regarding use_dictionary:** It is highly reccomended to use the "use_dictionary" parameter for "annotator" and "annotation_software".

**Example for annotations from IFCBProc**

| Key | Value |
| --- | --- |
| udt | udt1__usa_mc_lane_research_laboratories__imaging_flow_cytobot__225__1748567116__19 |
| udt_bin | 0x032dc621accf3dc224a43f022373c200006839044c9400f1b21cb527d7 |
| uuid | 0x486b38eefc0a4a1aa16a1ac3b0eb5ed8 |
| last_modified | 1762184586 |
| extents | 0, 400, 0, 600, 0, 3 |
| annotator | null |
| annotation_software | https://github.com/NOC-OI/ifcbproc |


## Annotation files

Each annotation is attached to a specific ROI, of a specific data frame. In a biological context, the most important metadata tag is usually "taxa", which should contain taxanomic information relative to the chosen authoratative taxonomy. Other metadata might be stored in an annotation however, such as particle size or other morphological measurements.

### Per-file metadata

| Key | Expected value |
| --- | --- |
| data_type | Literal string "CRAB_ANNOTATION_V1" |
| last_modified | uint64, Unix timestamp of last modification |
| references_udts | Concatenated binary string of binary compact UDTs referenced |
| x_<metadata_name\> | **(optional)** Arbitrary fields for use in application-specific scenarios |

**Example for annotations from EcoTaxa**

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
| uuid | In compact binary form, used as the unique identifier of the ROI referenced |
| last_modified | uint64, Unix timestamp of annotation modification time |
| annotator | String, an email address or ORCID identifier (MUST be formatted with dashes). MUST be null if no human involvement |
| annotation_software | String, URI reference to the software used to create the annotation, preferably the source code repository |
| field_<field_name\> | **(optional, but reccomended)** Arbitrary fields for use in annotation, common ones listed below |

**Common fields**

- taxon (e.g. https://www.gbif.org/species/8211946, or urn:lsid:marinespecies.org:taxname:149093)
- major_axis_um (e.g. 129)

When creating fields, it is always advisable to use URIs wherever possible. URIs are preferred as they are instantly recognisable, and allow new users to easily access further information. Parquet's dictionary compresson means that the excess size of URIs is not a problem for search or storage, so long as single, authorotative sources are used.

For taxonomic data, CRAB reccomends using GBIF URIs to refer to species. While a WoRMS LSID is a suitable alternative (and will be recognised by CRAB), a GBIF URI is more immediately usable when encountered in the wild, and is preferred for datasets intended for public distribution.

**Note regarding use_dictionary:** It is highly reccomended to use the "use_dictionary" parameter for "annotator", "annotation_software" and any other string field with high repitition. For biological data this usually includes fields such as "taxon" where there are a lot of duplicated string entries. With a lot of fields, it might make sense to increase the max dictionary size. Anaecdotally, around 2MB results in good performance on S3 backed storage, but decreased row group sizes of 32-64MB are needed for lower memory use.

**Example for annotations from EcoTaxa**

| Key | Value |
| --- | --- |
| udt | udt1__usa_mc_lane_research_laboratories__imaging_flow_cytobot__225__1748567116__19 |
| udt_bin | 0x032dc621accf3dc224a43f022373c200006839044c9400f1b21cb527d7 |
| uuid | 0x486b38eefc0a4a1aa16a1ac3b0eb5ed8 |
| last_modified | 1762184586 |
| annotator | alewin@noc.ac.uk |
| annotation_software | https://github.com/ecotaxa/ecotaxa |
| field_taxon | https://www.gbif.org/species/8211946 |
