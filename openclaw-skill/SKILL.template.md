<skill_schema>
  <name>search-ads</name>
  <description>
    Interact with the Search-ADS tool to search, manage, and analyze scientific papers from NASA ADS.
    Supports semantic search, adding papers by identifier/URL, managing notes, and retrieving paper details.
    Also provides "Maho's Insights" generation for the WebUI dashboard.
  </description>
  <tools>
    <tool_code>
      <name>search_ads_find</name>
      <description>Search for papers in the library or online using natural language context.</description>
      <parameters>
        <parameter>
          <name>context</name>
          <type>string</type>
          <description>The search query or context (e.g., "papers about M1 closure in CCSN").</description>
          <required>true</required>
        </parameter>
        <parameter>
          <name>limit</name>
          <type>integer</type>
          <description>Maximum number of results to return (default: 5).</description>
          <required>false</required>
        </parameter>
        <parameter>
          <name>local_only</name>
          <type>boolean</type>
          <description>If true, search only the local database. If false (default), may search online ADS.</description>
          <required>false</required>
        </parameter>
      </parameters>
      <command>
        __SEARCH_ADS_PYTHON__ -m src.cli.main find --context "{context}" --top-k {limit} {?local_only:--local}
      </command>
    </tool_code>

    <tool_code>
      <name>search_ads_seed</name>
      <description>Add a paper to the local library from NASA ADS by identifier or URL.</description>
      <parameters>
        <parameter>
          <name>identifier</name>
          <type>string</type>
          <description>The paper identifier (Bibcode, arXiv ID, DOI) or ADS URL.</description>
          <required>true</required>
        </parameter>
        <parameter>
          <name>project</name>
          <type>string</type>
          <description>Optional project name to tag the paper with.</description>
          <required>false</required>
        </parameter>
      </parameters>
      <command>
        __SEARCH_ADS_PYTHON__ -m src.cli.main seed "{identifier}" {?project:--project "{project}"}
      </command>
    </tool_code>

    <tool_code>
      <name>search_ads_show</name>
      <description>Show detailed information about a paper, including abstract.</description>
      <parameters>
        <parameter>
          <name>identifier</name>
          <type>string</type>
          <description>The paper identifier (Bibcode) or search query to find it.</description>
          <required>true</required>
        </parameter>
      </parameters>
      <command>
        __SEARCH_ADS_PYTHON__ -m src.cli.main show "{identifier}"
      </command>
    </tool_code>

    <tool_code>
      <name>search_ads_list</name>
      <description>List papers in the local library.</description>
      <parameters>
        <parameter>
          <name>limit</name>
          <type>integer</type>
          <description>Number of papers to list (default: 10).</description>
          <required>false</required>
        </parameter>
        <parameter>
          <name>sort_by</name>
          <type>string</type>
          <description>Sort order: 'date', 'citations', 'added' (default: 'added').</description>
          <required>false</required>
        </parameter>
      </parameters>
      <command>
        __SEARCH_ADS_PYTHON__ -m src.cli.main list-papers --limit {limit} --sort {sort_by}
      </command>
    </tool_code>

    <tool_code>
      <name>search_ads_note</name>
      <description>Add or view notes for a specific paper.</description>
      <parameters>
        <parameter>
          <name>identifier</name>
          <type>string</type>
          <description>The paper identifier (Bibcode).</description>
          <required>true</required>
        </parameter>
        <parameter>
          <name>content</name>
          <type>string</type>
          <description>The note content to add. If omitted, lists existing notes.</description>
          <required>false</required>
        </parameter>
      </parameters>
      <command>
        if [ -n "{content}" ]; then
          __SEARCH_ADS_PYTHON__ -m src.cli.main note add "{identifier}" "{content}"
        else
          __SEARCH_ADS_PYTHON__ -m src.cli.main note list "{identifier}"
        fi
      </command>
    </tool_code>
    
    <tool_code>
      <name>search_ads_pdf_download</name>
      <description>Download the PDF for a paper.</description>
      <parameters>
        <parameter>
          <name>identifier</name>
          <type>string</type>
          <description>The paper identifier (Bibcode).</description>
          <required>true</required>
        </parameter>
      </parameters>
      <command>
        __SEARCH_ADS_PYTHON__ -m src.cli.main pdf download "{identifier}"
      </command>
    </tool_code>

    <tool_code>
      <name>search_ads_sync</name>
      <description>Analyze recent papers in the library using AI and update Maho's Insights on the WebUI dashboard.</description>
      <parameters>
        <parameter>
          <name>limit</name>
          <type>integer</type>
          <description>Number of recent papers to analyze (default: 5).</description>
          <required>false</required>
        </parameter>
      </parameters>
      <command>
        __SEARCH_ADS_PYTHON__ __SKILL_DIR__/scripts/sync_insights.py {limit}
      </command>
    </tool_code>
  </tools>
</skill_schema>
