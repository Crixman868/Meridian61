def render_master_log():
    st.subheader("🗄️ System Workspace Overview")
    df = load_log_data()

    if df.empty:
        st.info("No active logs recorded in this workspace yet.")
    else:
        for idx, row in df.iterrows():
            m61_id = str(row.get('M61 ID', 'N/A'))
            client_name = str(row.get('Client', ''))
            ship_status = str(row.get("Status", "Active"))
            total_cartons = str(row.get("TOTAL CTNS", ""))
            inv_no = str(row.get("Invoice#", ""))
            container_no = str(row.get("Container #", ""))
            
            raw_eta = row.get("ETA")
            timestamp = pd.to_datetime(raw_eta, errors='coerce')
            current_date = timestamp.date() if not pd.isna(timestamp) else datetime.now().date()
            status_label, _ = get_eta_status(current_date, ship_status)
            
            naldo_val = str(row.get("NALDO", "No")).strip().upper()
            naldo_display = f"🔴 NALDO: YES" if naldo_val == "YES" else f"⚪ NALDO: NO"
            
            header_text = f"📦 CTNS: {total_cartons if total_cartons else '0'} | {status_label} | Client: {client_name if client_name else 'Unassigned'} | Inv: {inv_no if inv_no else 'Pending'} | Cont: {container_no if container_no else 'Pending'} | {m61_id}"

            with st.expander(header_text):
                col1, col2, col3, col4, col5, col6 = st.columns(6)
                # Unique keys for inputs
                new_cont = col1.text_input("Container #", value=container_no, key=f"cont_{m61_id}")
                new_orig = col2.selectbox("Country of Origin", ALL_COUNTRIES, index=ALL_COUNTRIES.index(row.get("Origin", "")) if row.get("Origin", "") in ALL_COUNTRIES else 0, key=f"orig_{m61_id}")
                new_eta = col3.date_input("ETA", value=current_date, key=f"eta_{m61_id}")
                new_lodg = col4.radio("Doc Status", ["Yes", "No"], index=0 if row.get("Doc Status") == "Yes" else 1, horizontal=True, key=f"lodged_{m61_id}")
                new_stat = col5.selectbox("Status", ["Active", "Delivered"], index=0 if ship_status != "Delivered" else 1, key=f"stat_{m61_id}")
                new_naldo = col6.radio("NALDO Override", ["Yes", "No"], index=0 if naldo_val == "YES" else 1, horizontal=True, key=f"naldo_{m61_id}")
                
                st.write("---")
                st.markdown("#### Document Control Matrix")
                
                grid = st.columns(5)
                upload_cache = {}
                
                for i, slot in enumerate(ALL_DOCS):
                    with grid[i % 5]:
                        st.markdown(f"**{slot}**")
                        file_link = str(row.get(slot, "")).strip()
                        
                        # Unique keys for buttons and uploaders
                        if file_link.startswith("http"):
                            st.link_button("📄 View Document", url=file_link, key=f"view_{m61_id}_{i}", use_container_width=True)
                        else:
                            st.button("Pending Upload", disabled=True, key=f"pend_{m61_id}_{i}", use_container_width=True)
                        
                        if slot in EXTERNAL_DOCS:
                            uploaded_file = st.file_uploader(f"Replace {slot}", key=f"up_{m61_id}_{i}", label_visibility="collapsed")
                            if uploaded_file:
                                upload_cache[slot] = uploaded_file
                
                if st.button("💾 Save Shipment Updates", key=f"save_{m61_id}", type="primary"):
                    with st.spinner("Processing structural workspace records..."):
                        df_update = load_log_data()
                        # Use the M61 ID to locate the row safely
                        row_indices = df_update.index[df_update['M61 ID'].astype(str) == m61_id].tolist()
                        if row_indices:
                            row_index = row_indices[0]
                            df_update.at[row_index, "Container #"] = new_cont
                            df_update.at[row_index, "Origin"] = new_orig
                            df_update.at[row_index, "ETA"] = str(new_eta)
                            df_update.at[row_index, "Doc Status"] = new_lodg
                            df_update.at[row_index, "Status"] = new_stat
                            df_update.at[row_index, "NALDO"] = new_naldo
                            
                            for slot_name, up_file in upload_cache.items():
                                doc_filename = f"{m61_id}_{slot_name.replace(' ', '_')}.pdf"
                                new_link = upload_physical_file_to_drive(up_file, doc_filename, client_name, m61_id)
                                if new_link: df_update.at[row_index, slot_name] = new_link
                                
                            if save_log_data(df_update):
                                st.success("✅ Log tracking entries synchronized!")
                                st.rerun()
